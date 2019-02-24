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

from bitcoin.core.serialize import uint256_to_shortstr
from bitcoin.core import b2lx

class MemPool(object):
    def __init__(self, log):
        self.pool = {}
        self.log = log

    def add(self, tx):
        hashstr = b2lx(tx.GetTxid())

        if hashstr in self.pool:
            self.log.info("MemPool.add(%s): already known" % (hashstr,))
            return False

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
