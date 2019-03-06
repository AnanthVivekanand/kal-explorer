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
from pybloom_live import BloomFilter
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

def input(*args):
    res = []
    for arg in args:
        res.append('test_%s' % arg)
    return res

def get_address_walletid(txn, addr):
    return txn.get(('addresses:{}'.format(addr)).encode())

def put_address_walletid(txn, addr, walletId):
    return txn.put(('addresses:{}'.format(addr)).encode(), walletId)

def get_address_map(txn, walletId):
    res = txn.get(('addressMap:{}'.format(walletId)).encode())
    if not res:
        res = set()
    else:
        res = pickle.loads(res)
    return res

def put_address_map(txn, walletId, addr):
    res = get_address_map(txn, walletId)
    res.add(addr)
    b = pickle.dumps(res)
    return txn.put(('addressMap:{}'.format(walletId)).encode(), b)

def del_address_map(txn, walletId):
    txn.delete(('addressMap:{}'.format(walletId)).encode())

def connect_input(batch, addrs):
    with env.begin(write=True) as txn:
        for addr in addrs:
            if addr is None:
                continue
            walletId = get_address_walletid(txn, addr)
            if not walletId:
                continue
            addressFilter = txn.get(walletId)
            if addressFilter is None:
                continue
            for addr in addrs:
                existingWalletId = get_address_walletid(txn, addr)
                if not existingWalletId:
                    put_address_walletid(txn, addr, walletId)
                    print('Added %s to wallet %s' % (addr, walletId))
                    batch.put(('walletAdd:%s' % addr).encode(), walletId)
                else:
                    mapDelete = set()
                    for existingAddr in get_address_map(txn, existingWalletId):
                        if existingWalletId != walletId:
                            # Delete entry in addressMap
                            # Point addresses to existing walletId
                            walletMerge[existingWalletId] = walletId
                            put_address_walletid(txn, existingAddr, walletId)
                            put_address_map(txn, walletId, addr)
                            mapDelete.add(existingWalletId)
                            # TODO: Need to update db?
                            print('Merged %s into %s' % (existingAddr, walletId))
                    for delete in mapDelete:
                        del_address_map(txn, delete)
            return
        # Create new wallet
        walletId = str(uuid.uuid4()).encode()
        for addr in addrs:
            if addr is None:
                continue
            put_address_walletid(txn, addr, walletId)
            put_address_map(txn, walletId, addr)
            print('Created wallet %s for %s' % (walletId, addr))
            batch.put(('walletCreate:%s' % walletId.decode()).encode(), addr.encode())
        txn.put(walletId, b'1')

# connect_input(input(1, 2, 3))
# connect_input(input(1))

# connect_input(input(1, 4))
# connect_input(input(5, 6))
# connect_input(input(4, 5))

# connect_input(input(7, 8, 9, 1))