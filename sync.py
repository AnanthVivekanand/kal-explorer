import logging
import bitcoin
import bitcointx
import gevent
from sync.chaindb import ChainDb
from sync.mempool import MemPool
from sync.sync import PeerManager
from bitcoin.core.script import CScript
from shared import settings

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

    P = settings.ChainParams
    params = P()
    print(params)
    bitcoin.params.MESSAGE_START = params.NETMAGIC
    bitcoin.params.BASE58_PREFIXES = params.BASE58_PREFIXES

    mempool = MemPool(logger)
    chaindb = ChainDb(logger, mempool, params)
    bitcointx.SelectAlternativeParams(settings.CoreChainParams, P)
    threads = []
    peermgr = PeerManager(logger, mempool, chaindb)
    c = peermgr.add(settings.NODE_IP, P.PORT)

    threads.append(c)

    for t in threads:
        t.start()
    try:
        gevent.joinall(threads, timeout=None, raise_error=True)
    finally:
        for t in threads:
            t.kill()
        gevent.joinall(threads)
