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

import os
import struct
import plyvel
import threading

class Cache(object):
    def __init__(self):
        self.db = plyvel.DB('/data/explorer/chainstate/', create_if_missing=True)
        # self.memCache = C(maxsize=1000)
    
    def clear(self):
        # self.fileCache.clear()
        pass

    def settop(self, h):
        return self.db.put(b'tip', h)

    def gettop(self):
        res = self.db.get(b'tip')
        if res:
            return res
        return bytes(bytearray.fromhex('0000000000000000000000000000000000000000000000000000000000000000'))

    def getheight(self):
        return struct.unpack('i', self.db.get(b'height', struct.pack('i', -1)))[0]
