# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
import struct
import hashlib
import copy
from io import BytesIO
import binascii
import gevent
import gevent.pywsgi
import socket
import random
import logging
import bitcoin
import bitcointx
from bitcointx.core import CTransaction, CheckTransaction
import traceback

import gevent.monkey
gevent.monkey.patch_all()

from redis import Redis
from shared import settings
from gevent import Greenlet
from bitcoin.messages import (msg_version, msg_ping, msg_verack, msg_getaddr,
messagemap, msg_getdata, msg_getblocks, msg_headers, msg_getheaders, msg_addr, 
msg_pong, msg_tx)
from bitcoin.net import CInv
from bitcoin.core import lx, b2lx
from sync.chaindb import ChainDb
from bitcoin.core.script import CScript
from sync.mempool import MemPool
from shared.settings import PROTO_VERSION, MIN_PROTO_VERSION, CADDR_TIME_VERSION, NOBLKS_VERSION_START, BIP0031_VERSION

MY_SUBVERSION = b"/KalExplorer:0.1.0/"

redis = Redis('%s' % settings.REDIS_HOST)
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

    def __init__(self, dstaddr, dstport, log, peermgr, mempool, chaindb : ChainDb):
        Greenlet.__init__(self)
        self.dstaddr = dstaddr
        self.dstport = dstport
        self.mempool = mempool
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

        gevent.spawn(self.broadcast_listen)
        # asyncio.get_event_loop().run_until_complete(self.broadcast_listen())

    def broadcast_listen(self):
        pubsub = redis.pubsub()
        pubsub.subscribe('broadcast')
        for msg in pubsub.listen():
            tx = msg['data']
            try:
                tx = tx.decode()
                btx = bytes.fromhex(tx)
                tx = CTransaction.deserialize(btx)
                # CheckTransaction(tx) # TODO: Fix money supply?
                msg = msg_tx()
                msg.tx = tx
                self.send_message(msg)
                print('Sent tx %s' % b2lx(msg.tx.GetTxid()))
                if self.chaindb.tx_is_orphan(msg.tx):
                    self.log.info("MemPool: Ignoring orphan TX %s" % (b2lx(msg.tx.GetHash()),))
                else:
                    self.chaindb.mempool_add(msg.tx)
            except Exception as e:
                print(e)
                traceback.print_exc()

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

    def send_getblocks(self, timecheck=True):
        if not self.getblocks_ok:
            return
        now = time.time()
        # if timecheck and (now - self.last_getblocks) < 1:
        #     return
        self.last_getblocks = now

        our_height = self.chaindb.getheight()
        if our_height < 0:
            gd = msg_getdata(self.ver_send)
            inv = CInv()
            inv.type = 2
            inv.hash = bitcoin.params.GENESIS_BLOCK.GetHash()
            gd.inv.append(inv)
            self.send_message(gd)
        elif our_height < self.remote_height:
            gb = msg_getblocks(self.ver_send)
            if our_height >= 0:
                gb.locator.vHave = self.chaindb.getlocator()
            self.send_message(gb)

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
            # if self.ver_send >= CADDR_TIME_VERSION:
                # self.send_message(msg_getaddr(self.ver_send))
            self.send_getblocks()

        elif message.command == b'ping':
            if self.ver_send > BIP0031_VERSION:
                self.send_message(msg_pong(self.ver_send))
        
        elif message.command == b"verack":
            self.ver_recv = self.ver_send
            self.send_message(msg_addr())
            # self.send_getaddr()

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
                # break #UNDO
                self.last_want = i.hash
            if len(want.inv):
                self.send_message(want)

        elif message.command == b"tx":
            if self.chaindb.tx_is_orphan(message.tx):
                self.log.info("MemPool: Ignoring orphan TX %s" % (b2lx(message.tx.GetHash()),))
            # elif not self.chaindb.tx_signed(message.tx, None, True):
            #     self.log.info("MemPool: Ignoring failed-sig TX %s" % (b2lx(message.tx.GetHash()),))
            else:
                self.chaindb.mempool_add(message.tx)

        elif message.command == b"block":
            bhash = b2lx(message.block.GetHash())
            self.chaindb.putblock(message.block)
            # b = BytesIO()
            # message.block.stream_serialize(b)
            # s = b.getvalue()
            # print(b2lx(s))
            self.last_block_rx = time.time()
            #UNDO
            if self.last_want == 0:
                gevent.spawn(self.send_getblocks)
            elif bhash == b2lx(self.last_want):
                gevent.spawn(self.send_getblocks)

        elif message.command == b"getheaders":
            self.getheaders(message)
        # elif message.command == b"addr":
            # if len(message.addrs) == 1:
            #     gevent.spawn(self.send_getblocks)
            # for addr in message.addrs:
            #     host = '%s:%s' % (addr.ip, addr.port)
            #     if host not in self.addresses_seen:
            #         self.addresses_seen.append(host)

        # elif message.command == b'tx':
        #      for idx, vout in enumerate(message.tx.vout):
        #         script = vout.scriptPubKey
        #         if len(script) >= 38 and script[:6] == bitcoin.core.WITNESS_COINBASE_SCRIPTPUBKEY_MAGIC:
        #             continue
        #         script = CScript(vout.scriptPubKey)
        #         if script.is_unspendable():
        #             print("Unspendable %s" % vout.scriptPubKey)
        #             if vout.scriptPubKey[:4] == b'j\x07\xfe\xab':
        #                 print(vout.scriptPubKey[4:].decode('utf-8'))
        #             continue

        last_blkmsg = time.time() - self.last_block_rx
        if last_blkmsg > 5:
            self.send_getblocks()

    def getheaders(self, message):
        msg = msg_getheaders()
        msg.nVersion = PROTO_VERSION
        msg.locator.vHave = self.chaindb.getlocator()
        # msg.vHave = [bytearray.fromhex('2ada80bf415a89358d697569c96eb98cdbf4c3b8878ac5722c01284492e27228')]
        # msg.hashstop = bytearray.fromhex('2ada80bf415a89358d697569c96eb98cdbf4c3b8878ac5722c01284492e27228')
        self.send_message(msg)

class PeerManager(object):
    def __init__(self, log, mempool, chaindb):
        self.log = log
        self.mempool = mempool
        self.chaindb = chaindb
        self.peers = []
        self.addrs = {}
        self.tried = {}

    def add(self, host, port):
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
