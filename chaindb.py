
import struct
import os, sys
import bitcoin
import binascii
import json
from datetime import datetime
from cache import Cache
from models import *

from bitcoin.core import b2lx, uint256_from_str
from bitcoin.core.serialize import uint256_from_str
from bitcoin.wallet import CBitcoinAddress
from bitcoin.core.script import CScript
from bitcointx.wallet import CBitcoinAddress as TX_CBitcoinAddress



class ChainDb(object):

    def __init__(self, log):
        self.log = log
        self.utxo_changes = 0
        self.cache = Cache()
        self.cache.clear()
        self.db = self.cache.db
        self.address_changes = {}
        self.address_change_count = 0
        self.utxo_cache = {}

    def locate(self, locator):
        return 0

    def gettophash(self):
        return self.cache.gettop()

    def haveblock(self, sha256, _):
        return False

    def getheight(self):
        return self.cache.getheight()

    def pututxo(self, txid, vout, address, value):
        key = ('%s:%s' % (txid, vout)).encode()
        data = ('%s:%s' % (address, value)).encode()
        self.utxo_cache[key] = data

    def poputxo(self, wb, txid, vout):
        key = ('%s:%s' % (txid, vout)).encode()
        if key in self.utxo_cache:
            r = self.utxo_cache[key]
            del self.utxo_cache[key]
        else:
            r = self.db.get(key)
            wb.delete(key)
        r = r.decode("utf-8").split(':')
        return (r[0], int(r[1]))

    def putoneblock(self, block, initsync=True):
        if block.hashPrevBlock != self.gettophash():
            print("Cannot connect block to chain %s %s" % (b2lx(block.GetHash()), b2lx(self.gettophash())))
            return
        height = struct.unpack('i', self.db.get(b'height', struct.pack('i', -1)))[0] + 1
        bHash = b2lx(block.GetHash())
        # print(dir(block))
        # print(b2lx(block.hashMerkleRoot))
        # print(b2lx(block.GetHash()))
        # print(block.calc_difficulty(block.nBits))
        # print(datetime.utcfromtimestamp(block.nTime).strftime('%Y-%m-%d %H:%M:%S'))
        # print(b2lx(struct.pack('i', block.nVersion)))
        # print(height)
        # print(b2lx(struct.pack('i', block.nBits)))
        # print(block.nNonce)
        # print(len(block.serialize())) # size
        # raise
        with self.db.write_batch(transaction=True) as wb:
            wb.put(('block:%s' % bHash).encode(), json.dumps({
                'merkle_root': b2lx(block.hashMerkleRoot), # save merkle root as hex string
                'difficulty': block.calc_difficulty(block.nBits), # save difficulty as both calculated and nBits
                'timestamp': datetime.utcfromtimestamp(block.nTime).strftime('%Y-%m-%d %H:%M:%S'),
                'version': block.nVersion, # we can do binary operation if saved as binary
                'height': height,
                'bits': block.nBits,
                'nonce': block.nNonce,
                'size': len(block.serialize()),
                'hash': bHash,
                'coinbase': str(block.vtx[0].vin[0].scriptSig),
            }).encode())
            for tx in block.vtx:
                txid = b2lx(tx.GetHash())
                for idx, vout in enumerate(tx.vout):
                    script = vout.scriptPubKey
                    if len(script) >= 38 and script[:6] == bitcoin.core.WITNESS_COINBASE_SCRIPTPUBKEY_MAGIC:
                        pass
                    else:
                        try:
                            script = CScript(vout.scriptPubKey)
                            if script.is_unspendable():
                                continue
                            address = str(TX_CBitcoinAddress.from_scriptPubKey(script))
                        except:
                            print('scriptPubKey invalid txid=%s scriptPubKey=%s value=%s' % (txid, b2lx(vout.scriptPubKey), vout.nValue))
                            continue
                        value = vout.nValue
                        self.pututxo(txid, idx, address, value)
                        # TODO utxo database
                        self.utxo_changes += 1
                        if address in self.address_changes:
                            self.address_changes[address] += value
                        else:
                            self.address_changes[address] = value
                for idx, vin in enumerate(tx.vin):
                    if tx.is_coinbase() and idx == 0:
                        continue
                    # TODO mark utxo as spent, don't remove
                    preaddress, prevalue = self.poputxo(wb, b2lx(vin.prevout.hash), vin.prevout.n)
                    if preaddress in self.address_changes:
                        self.address_changes[preaddress] -= prevalue
                    else:
                        self.address_changes[preaddress] = -prevalue
            
            with self.db.write_batch(transaction=True) as addressBatch:
                for key, value in self.address_changes.items():
                    temp = {'address': key, 'balance_change': value}
                    k = ('address:%s' % key).encode()
                    currbal = struct.unpack('l', self.db.get(k, struct.pack('l', 0)))[0]
                    addressBatch.put(k, struct.pack('l', currbal + value))
                    self.address_change_count += 1
            self.address_changes = {}
            
            if not initsync or self.address_change_count > 10000:
                print('Commiting address balance updates')
                sys.stdout.flush()
                changes_list = []
                self.address_change_count = 0
                with self.db.write_batch(transaction=True) as deleteBatch:
                    for key, value in self.db.iterator(prefix=b'address:'):
                        value = struct.unpack('l', value)[0]
                        address = key.decode('utf-8').split(':')[1]
                        changes_list.append({'address': address, 'balance_change': value})
                        deleteBatch.delete(key)
                    AddressChanges.insert_many(changes_list).execute()
                db.execute_sql("insert into address (address, balance) (select address, sum(balance_change) as balance_change from addresschanges group by address) on conflict(address) do update set balance = address.balance + EXCLUDED.balance; TRUNCATE addresschanges;")

            if not initsync or height % 100 == 0:
                print('Commit blocks')
                blocks = []
                with self.db.write_batch(transaction=True) as deleteBatch:
                    for key, value in self.db.iterator(prefix=b'block:'):
                        data = json.loads(value.decode('utf-8'))
                        data['version'] = struct.pack('i', data['version'])
                        data['bits'] = struct.pack('i', data['bits'])
                        blocks.append(data)
                        deleteBatch.delete(key)
                    if blocks:
                        Block.insert_many(blocks).execute()


            h = block.GetHash()
            wb.put(b'tip', h)
            wb.put(b'height', struct.pack('i', height))

            for key, value in self.utxo_cache.items():
                wb.put(key, value)
            self.utxo_cache = {}
            
            print("UpdateTip: %s height %s" % (b2lx(h), height))
            return True
        # print((block.hashPrevBlock))
        # print(b2lx(block.GetHash()))
        # print(block.hashPrevBlock)
        # print(self.top)
        # if not self.have_prevblock(block):
        # 	self.orphans[block.sha256] = True
        # 	self.orphan_deps[block.hashPrevBlock] = block
        # 	self.log.write("Orphan block %064x (%d orphans)" % (block.sha256, len(self.orphan_deps)))
        # 	return False
    def putblock(self, block):
        if self.haveblock(block.GetHash(), True):
            self.log.write("Duplicate block %064x submitted" % (block.GetHash(), ))
            return False
        return self.putoneblock(block)