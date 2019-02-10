import logging
import bitcoin
import bitcointx
import gevent
from sync.chaindb import ChainDb
from sync.mempool import MemPool
from sync.sync import PeerManager
from bitcoin.core.script import CScript

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
    ch.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    P = TUXParams
    params = P()
    bitcoin.params.MESSAGE_START = params.NETMAGIC
    bitcoin.params.BASE58_PREFIXES = params.BASE58_PREFIXES

    mempool = MemPool(logger)
    chaindb = ChainDb(logger, mempool, params)
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
