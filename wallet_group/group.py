# 1. Get new transaction inputs
# 2. Use bloom filter to get deltas for existing addresses with wallet id
# 3. Create wallets for new addresses
# 4. Apply deltas to wallets, check address model for false positive bloom filter


# Models:
# wallet - addressFilter
# address - walletId
import uuid
import lmdb
import pickle
from io import BytesIO

# Wallet.BLOOM_ADDRESSES = 3000000; // 3 million
# Wallet.BLOOM_FPR = 0.01; // false positive rate

# class Wallet(object):
#     addressFilter = BloomFilter(3000000, 0.01)

# addressMap = {} # walletId -> address
walletMerge = {}

env = lmdb.open('/data/explorer/wallets', max_dbs=1, map_size=int(1e9))
# main = env.open_db()
# with env.begin(write=True) as txn:
#     txn.drop(main, delete=True)

class WalletGroup(object):

    def __init__(self, path, drop=False):
        env = lmdb.open('/data/explorer/wallets', max_dbs=1, map_size=int(1e9))
        if drop:
            main = env.open_db()
            with env.begin(write=True) as txn:
                txn.drop(main, delete=True)

    def get_address_walletid(self, txn, addr):
        return txn.get(('addresses:{}'.format(addr)).encode())

    def put_address_walletid(self, txn, addr, walletId):
        return txn.put(('addresses:{}'.format(addr)).encode(), walletId)

    def get_address_map(self, txn, walletId):
        res = txn.get(('addressMap:{}'.format(walletId)).encode())
        if not res:
            res = set()
        else:
            res = pickle.loads(res)
        return res

    def put_address_map(self, txn, walletId, addr):
        res = self.get_address_map(txn, walletId)
        res.add(addr)
        b = pickle.dumps(res)
        return txn.put(('addressMap:{}'.format(walletId)).encode(), b)

    def del_address_map(self, txn, walletId):
        txn.delete(('addressMap:{}'.format(walletId)).encode())

    def create(self, txn, batch, addrs):
        # Create new wallet
        walletId = str(uuid.uuid4()).encode()
        for addr in addrs:
            if addr is None:
                continue
            self.put_address_walletid(txn, addr, walletId)
            self.put_address_map(txn, walletId, addr)
            print('Created wallet %s for %s' % (walletId.decode(), addr))
            batch.put(('walletCreate:%s' % addr).encode(), walletId)
        txn.put(walletId, b'1')

    def connect_input(self, batch, addrs):
        with env.begin(write=True) as txn:

            walletId = None
            for addr in addrs:
                _walletId = self.get_address_walletid(txn, addr)
                if walletId is None:
                    walletId = _walletId

            if not walletId:
                # Create
                return self.create(txn, batch, addrs)

            for addr in addrs:
                # Loop overall addresses and determine whether to add or merge into walletId
                existingWalletId = self.get_address_walletid(txn, addr)
                # addressFilter = txn.get(walletId)
                # if addressFilter is None:
                #     continue
                if not existingWalletId:
                    self.put_address_walletid(txn, addr, walletId)
                    self.put_address_map(txn, walletId, addr)
                    print('Added %s to wallet %s' % (addr, walletId))
                    batch.put(('walletAdd:%s' % addr).encode(), walletId)
                elif walletId != existingWalletId:
                    mapDelete = set()
                    # Update all other addresses with merge
                    for existingAddr in self.get_address_map(txn, existingWalletId):
                        # Point addresses to existing walletId
                        self.put_address_walletid(txn, existingAddr, walletId)
                        # Add address to walletId set
                        self.put_address_map(txn, walletId, existingAddr)
                        # Delete existing walletId set
                        mapDelete.add(existingWalletId)
                        batch.put(('walletMerge:%s' % existingWalletId.decode()).encode(), walletId)
                        print('Merged %s from %s into %s' % (existingAddr, existingWalletId, walletId))
                    for delete in mapDelete:
                        self.del_address_map(txn, delete)
                    txn.delete(existingWalletId)

# class DB(object):

#     def put(self, k, v):
#         pass

# def pprint():
#     with env.begin(write=True) as txn:
#         cursor = txn.cursor()
#         for k, v in cursor:
#             print(k, v)

# db = DB()
# connect_input(db, input(1))
# connect_input(db, input(1, 2))
# connect_input(db, input(2))
# connect_input(db, input(3, 2))
# connect_input(db, input(9, 8))
# connect_input(db, input(9, 1))
# pprint()
