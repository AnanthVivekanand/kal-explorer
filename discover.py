import time
import struct
import hashlib
import copy
from io import BytesIO
import gevent
import gevent.pywsgi
import socket
import random
import logging
from gevent import Greenlet
import bitcoin
import bitcointx
from bitcoin.messages import (msg_version, msg_ping, msg_verack, msg_getaddr,
messagemap, msg_getdata, msg_getblocks, msg_headers, msg_getheaders, msg_addr,
msg_pong)
from bitcoin.net import CInv
from bitcoin.core import lx, b2lx
from chaindb import ChainDb
from bitcoin.core.script import CScript


PROTO_VERSION = 70002
MIN_PROTO_VERSION = 70002
CADDR_TIME_VERSION = 31402
NOBLKS_VERSION_START = 60002
MY_SUBVERSION = b"/pynode:0.0.1/"
BIP0031_VERSION = 60000


settings = {}
debugnet = False

def verbose_sendmsg(message):
    if debugnet:
        return True
    if message.command != 'getdata':
        return True
    return False

def verbose_recvmsg(message):
    skipmsg = {
        b'tx',
        b'block',
        b'inv',
        b'addr'
    }
    if debugnet:
        return True
    if message.command in skipmsg:
        return False
    return True

class NodeConn(Greenlet):
    def __init__(self, dstaddr, dstport, log, peermgr, mempool, chaindb):
        Greenlet.__init__(self)
        self.dstaddr = dstaddr
        self.dstport = dstport
        self.log = log
        self.chaindb = chaindb
        self.sock = gevent.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.recvbuf = b""
        self.ver_send = MIN_PROTO_VERSION
        self.ver_recv = MIN_PROTO_VERSION
        self.last_sent = 0
        self.getblocks_ok = True
        self.last_block_rx = time.time()
        self.last_getblocks = 0
        self.remote_height = -1
        self.last_want = 0
        self.addresses_seen = []
        self.peermgr = peermgr

        self.hash_continue = None

        self.log.info("connecting")

        try:
            self.sock.connect((dstaddr, dstport))
        except:
            self.handle_close()
        vt = msg_version()
        vt.addrTo.ip = self.dstaddr
        vt.addrTo.port = self.dstport
        vt.addrFrom.ip = "0.0.0.0"
        vt.addrFrom.port = 0
        vt.nVersion = PROTO_VERSION
        vt.nStartingHeight = 0
        vt.strSubVer = MY_SUBVERSION
        self.send_message(vt)

    def _run(self):
        self.log.info(self.dstaddr + " connected")
        while True:
            try:
                t = self.sock.recv(8192)
                if len(t) <= 0: raise ValueError
            except (IOError, ValueError):
                self.handle_close()
                raise
            self.recvbuf += t
            self.got_data()

    def handle_close(self):
        self.log.info(self.dstaddr + " close")
        self.recvbuf = b""
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.close()
        except:
            pass

    def got_data(self):
        while True:
            if len(self.recvbuf) < 4:
                return
            if self.recvbuf[:4] != bitcoin.params.MESSAGE_START:
                raise ValueError("got garbage %s" % repr(self.recvbuf))
            # check checksum
            if len(self.recvbuf) < 4 + 12 + 4 + 4:
                return
            command = self.recvbuf[4:4+12].split(b"\x00", 1)[0]
            msglen = struct.unpack(b"<i", self.recvbuf[4+12:4+12+4])[0]
            checksum = self.recvbuf[4+12+4:4+12+4+4]
            if len(self.recvbuf) < 4 + 12 + 4 + 4 + msglen:
                return
            msg = self.recvbuf[4+12+4+4:4+12+4+4+msglen]
            th = hashlib.sha256(msg).digest()
            h = hashlib.sha256(th).digest()
            if checksum != h[:4]:
                raise ValueError("got bad checksum %s" % repr(self.recvbuf))
            self.recvbuf = self.recvbuf[4+12+4+4+msglen:]
            if command in messagemap:
                t = messagemap[command]
                t = t.msg_deser(BytesIO(msg))
                self.got_message(t)
            else:
                self.log.info("UNKNOWN COMMAND %s %s" % (command, repr(msg)))

    def send_message(self, message):
        if verbose_sendmsg(message):
            self.log.info("send %s" % repr(message))

        tmsg = message.to_bytes()

        try:
            self.sock.sendall(tmsg)
            self.last_sent = time.time()
        except:
            self.handle_close()

    def send_getaddr(self):
        self.send_message(msg_getaddr())

    def got_message(self, message):
        gevent.sleep()

        if self.last_sent + 30 * 60 < time.time():
            self.send_message(msg_ping(self.ver_send))

        if verbose_recvmsg(message):
            self.log.info("recv %s" % repr(message))

        if message.command == b"version":
            self.ver_send = min(PROTO_VERSION, message.nVersion)
            if self.ver_send < MIN_PROTO_VERSION:
                self.log.info("Obsolete version %d, closing" % (self.ver_send,))
                self.handle_close()
                return

            self.remote_height = message.nStartingHeight
            self.send_message(msg_verack(self.ver_send))

            if self.ver_send >= CADDR_TIME_VERSION:
                self.send_message(msg_getaddr(self.ver_send))
            
            # self.send_getblocks()

        elif message.command == b'ping':
            if self.ver_send > BIP0031_VERSION:
                self.send_message(msg_pong(self.ver_send))
        
        elif message.command == b"verack":
            self.ver_recv = self.ver_send
            self.send_message(msg_addr())
            self.send_getaddr()

        elif message.command == b"inv":

            # special message sent to kick getblocks
            # if (len(message.inv) == 1 and
            #     message.inv[0].type == MSG_BLOCK and
            #     self.chaindb.haveblock(message.inv[0].hash, True)):
            #     self.send_getblocks(False)
            #     return

            want = msg_getdata(self.ver_send)
            for i in message.inv:
                if i.type == 1:
                    want.inv.append(i)
                elif i.type == 2:
                    want.inv.append(i)
                self.last_want = i.hash
            if len(want.inv):
                self.send_message(want)

        # elif message.command == b"block":
        #     bhash = b2lx(message.block.GetHash())
        #     self.chaindb.putblock(message.block)
        #     self.last_block_rx = time.time()
        #     if self.last_want == 0:
        #         gevent.spawn(self.send_getblocks)
        #     elif bhash == b2lx(self.last_want):
        #         gevent.spawn(self.send_getblocks)
        elif message.command == b"addr":
            self.peermgr.new_addrs(message.addrs)
            for addr in message.addrs:
                self.peermgr.add(addr.ip, addr.port)
        elif message.command == b'getheaders':
            self.send_message(msg_headers())

class PeerManager(object):
    def __init__(self, log, mempool, chaindb):
        self.log = log
        self.mempool = mempool
        self.chaindb = chaindb
        self.peers = []
        self.addrs = {}
        self.tried = {}

    def add(self, host, port):
        if host in self.tried:
            return
        self.log.info("PeerManager: connecting to %s:%d" %
                   (host, port))
        self.tried[host] = True
        c = NodeConn(host, port, self.log, self, self.mempool,
                 self.chaindb)
        self.peers.append(c)
        return c

    def new_addrs(self, addrs):
        for addr in addrs:
            if addr.ip in self.addrs:
                continue
            self.addrs[addr.ip] = addr

        self.log.info("PeerManager: Received %d new addresses (%d addrs, %d tried)" %
                (len(addrs), len(self.addrs),
                 len(self.tried)))

    def random_addrs(self):
        ips = self.addrs.keys()
        random.shuffle(ips)
        if len(ips) > 1000:
            del ips[1000:]

        vaddr = []
        for ip in ips:
            vaddr.append(self.addrs[ip])

        return vaddr

    def closeall(self):
        for peer in self.peers:
            peer.handle_close()
        self.peers = []

class CoreChainParams(bitcointx.core.CoreChainParams):
    """Define consensus-critical parameters of a given instance of the Bitcoin system"""
    MAX_MONEY = None
    GENESIS_BLOCK = None
    PROOF_OF_WORK_LIMIT = None
    SUBSIDY_HALVING_INTERVAL = None
    NAME = None


class GRLCParams(CoreChainParams):
    RPC_PORT = 42075
    NETMAGIC = b"\xd2\xc6\xb6\xdb"
    BASE58_PREFIXES = {'PUBKEY_ADDR':38,
                       'SCRIPT_ADDR':50,
                       'SECRET_KEY' :176,
                       'EXTENDED_PUBKEY': b'\x04\x88\xb2\x1e',
                       'EXTENDED_PRIVKEY': b'\x04\x88\xad\xe4'}
    BECH32_HRP = 'grlc'

class TUXParams(CoreChainParams):
    RPC_PORT = 42072
    NETMAGIC = b"\xfc\xc5\xbf\xda"
    BASE58_PREFIXES = {'PUBKEY_ADDR':65,
                       'SCRIPT_ADDR':64,
                       'SECRET_KEY' :193,
                       'EXTENDED_PUBKEY': b'\x04\x88\xb2\x1e',
                       'EXTENDED_PRIVKEY': b'\x04\x88\xad\xe4'}
    BECH32_HRP = 'tux'

if __name__ == "__main__":
    logger = logging.getLogger("sync")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    mempool = None
    chaindb = ChainDb(logger)
    P = TUXParams
    params = P()
    bitcoin.params.MESSAGE_START = params.NETMAGIC
    bitcoin.params.BASE58_PREFIXES = params.BASE58_PREFIXES
    bitcointx.SelectAlternativeParams(CoreChainParams, P)
    threads = []
    peermgr = PeerManager(logger, mempool, chaindb)
    c = peermgr.add('45.77.228.139', 42071)

    threads.append(c)

    for t in threads:
        t.start()
    try:
        gevent.joinall(threads, timeout=None, raise_error=True)
    finally:
        for t in threads:
            t.kill()
        gevent.joinall(threads)
