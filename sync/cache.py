import os
import struct
import plyvel
# from cacheout import Cache as C
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
