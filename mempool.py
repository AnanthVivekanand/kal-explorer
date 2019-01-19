from bitcoin.core.serialize import uint256_to_shortstr
from bitcoin.core import b2lx

class MemPool(object):
    def __init__(self, log):
        self.pool = {}
        self.log = log

    def add(self, tx):
        hashstr = b2lx(tx.GetHash())

        if hashstr in self.pool:
            self.log.info("MemPool.add(%s): already known" % (hashstr,))
            return False
        # if not tx.is_valid():
        #     self.log.info("MemPool.add(%s): invalid TX" % (hashstr, ))
        #     return False

        self.pool[hashstr] = tx

        self.log.info("MemPool.add(%s), poolsz %d" % (hashstr, len(self.pool)))

        return True

    def remove(self, hashstr):
        if hashstr not in self.pool:
            return False

        del self.pool[hashstr]
        return True

    def size(self):
        return len(self.pool)
