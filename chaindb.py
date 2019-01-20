
import gevent
import string
import struct
import os, sys
import bitcoin
import binascii
import json
import threading
from datetime import datetime
from cache import Cache
from models import *

from bitcoin.core import b2lx, uint256_from_str
from bitcoin.core.serialize import uint256_from_str
from bitcoin.wallet import CBitcoinAddress
from bitcoin.core.script import CScript
from bitcointx.wallet import CBitcoinAddress as TX_CBitcoinAddress
from datetime import datetime, timedelta

class TxIdx(object):
    def __init__(self, blkhash, spentmask=0):
        self.blkhash = blkhash
        self.spentmask = spentmask

class ChainDb(object):

    def __init__(self, log, mempool):
        self.log = log
        self.mempool = mempool
        self.utxo_changes = 0
        self.cache = Cache()
        self.cache.clear()
        self.db = self.cache.db
        self.address_changes = {}
        self.address_change_count = 0
        self.transaction_change_count = 0
        self.utxo_cache = {}
        self.tx_lock = False
        self.checktransactions(True)
        self.checkaddresses(True)
        self.checkblocks(0, True)
        self.initial_sync = True

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

    def getutxo(self, txid, vout):
        key = ('%s:%s' % (txid, vout)).encode()
        if key in self.utxo_cache:
            r = self.utxo_cache[key]
        else:
            r = self.db.get(key)
        r = r.decode("utf-8").split(':')
        return (r[0], int(r[1]))

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

    def _committransactions(self):
        if self.tx_lock:
            return
        self.tx_lock = True
        count = 0
        loop = False
        first = True
        try:
            while loop or first:
                first = False
                self.log.debug('Commiting transaction updates')
                with self.db.write_batch(transaction=True) as deleteBatch:
                    transactions = []
                    with self.db.snapshot() as sn:
                        for key, value in sn.iterator(prefix=b'transaction:'):
                            txid = key.decode('utf-8').split(':')[1]
                            count += 1
                            data = json.loads(value.decode('utf-8'))
                            transactions.append({
                                "txid": txid,
                                "vin": data["vin"],
                                "vout": data["vout"],
                                "input_value": data["input_value"],
                                "output_value": data["output_value"],
                                "block": data["block"],
                                "addresses_out": data["addresses_out"],
                                "addresses_in": data["addresses_in"],
                                "timestamp": data["timestamp"],
                            })
                            deleteBatch.delete(key)
                            if count > 20000:
                                count = 0
                                loop = True
                                break
                        if len(transactions) > 0:
                            Transaction.insert_many(transactions).execute()
                            self.transaction_change_count -= count
        finally:
            self.tx_lock = False
            self.log.debug('Transaction update complete')

    def checktransactions(self, force=False):
        if not force and (self.tx_lock or self.transaction_change_count < 500):
            return
        t = threading.Thread(target=self._committransactions)
        t.daemon = True
        t.start()

    def checkaddresses(self, force=False):
        if force or self.address_change_count > 10000:
            self.log.debug('Commiting address balance updates')
            sys.stdout.flush()
            changes_list = []
            self.address_change_count = 0
            with self.db.write_batch(transaction=True) as deleteBatch:
                for key, value in self.db.iterator(prefix=b'address:'):
                    value = struct.unpack('l', value)[0]
                    address = key.decode('utf-8').split(':')[1]
                    changes_list.append({'address': address, 'balance_change': value})
                    deleteBatch.delete(key)
                if len(changes_list) > 0:
                    AddressChanges.insert_many(changes_list).execute()
            db.execute_sql("insert into address (address, balance) (select address, sum(balance_change) as balance_change from addresschanges group by address) on conflict(address) do update set balance = address.balance + EXCLUDED.balance; TRUNCATE addresschanges;")

    def checkblocks(self, height, force=False):
        if force or height % 300 == 0:
            self.log.debug('Commit blocks')
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

    def mempool_add(self, tx):
        self.mempool.add(tx)
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        tx = self.parse_tx(timestamp, None, None, tx)
        Transaction.insert_many([tx]).execute()

    def mempool_remove(self, txid):
        self.mempool.remove(txid)
        Transaction.delete().where(Transaction.txid == txid).execute()

    def parse_vin(self, tx, txid, tx_data, vin, idx, batch=None):
        if tx.is_coinbase() and idx == 0:
            tx_data["vin"].append({"address": None, "value": 0})
            tx_data["addresses_in"][None] = 0
            return
        # TODO mark utxo as spent, don't remove
        if batch:
            preaddress, prevalue = self.poputxo(batch, b2lx(vin.prevout.hash), vin.prevout.n)
            self.spend_txout(b2lx(vin.prevout.hash), vin.prevout.n, batch)
        else:
            preaddress, prevalue = self.getutxo(b2lx(vin.prevout.hash), vin.prevout.n)
        tx_data["vin"].append({"address": preaddress, "value": prevalue})
        tx_data["input_value"] += prevalue
        if preaddress in tx_data["addresses_in"]:
            tx_data["addresses_in"][preaddress] += prevalue
        else:
            tx_data["addresses_in"][preaddress] = prevalue
        if batch:
            if preaddress in self.address_changes:
                self.address_changes[preaddress] -= prevalue
            else:
                self.address_changes[preaddress] = -prevalue

    def parse_vout(self, tx, txid, tx_data, vout, idx):
        script = vout.scriptPubKey
        if len(script) >= 38 and script[:6] == bitcoin.core.WITNESS_COINBASE_SCRIPTPUBKEY_MAGIC:
            return
        try:
            script = CScript(vout.scriptPubKey)
            if script.is_unspendable():
                print("Unspendable %s" % vout.scriptPubKey)
                if vout.scriptPubKey[2:4] == b'\xfe\xab':
                    m = vout.scriptPubKey[4:].decode('utf-8')
                    Message.create(message=m)
                return
            address = str(TX_CBitcoinAddress.from_scriptPubKey(script))
        except:
            print('scriptPubKey invalid txid=%s scriptPubKey=%s value=%s' % (txid, b2lx(vout.scriptPubKey), vout.nValue))
            return
        value = vout.nValue
        self.pututxo(txid, idx, address, value)
        tx_data["vout"].append({"address": address, "value": value})
        if address in tx_data["addresses_out"]:
            tx_data["addresses_out"][address] += value
        else:
            tx_data["addresses_out"][address] = value
        tx_data["output_value"] += value
        # TODO utxo database
        self.utxo_changes += 1
        if address in self.address_changes:
            self.address_changes[address] += value
        else:
            self.address_changes[address] = value

    def parse_tx(self, timestamp, bHash, bHeight, tx, batch=None):
        txid = b2lx(tx.GetHash())
        tx_data = {
            "txid": txid,
            "vout": [], 
            "vin": [], 
            "input_value": 0, 
            "output_value": 0, 
            "block": bHash, 
            "block_height": bHeight, 
            "addresses_in": {}, 
            "addresses_out": {}, 
            "timestamp": timestamp
        }
        for idx, vin in enumerate(tx.vin):
            self.parse_vin(tx, txid, tx_data, vin, idx, batch)
        for idx, vout in enumerate(tx.vout):
            self.parse_vout(tx, txid, tx_data, vout, idx)
        if batch:
            batch.put(('transaction:%s' % txid).encode(), json.dumps(tx_data).encode())
            self.transaction_change_count += 1
        return tx_data

    def parse_vtx(self, vtx, wb, timestamp, bHash, bHeight):
        neverseen = 0
        for tx in vtx:
            txid = b2lx(tx.GetHash())

            if not self.mempool_remove(txid):
                neverseen += 1
            txidx = TxIdx(b2lx(bHash))
            if not self.puttxidx(txid, txidx, batch=wb):
                self.log.warn("TxIndex failed %s" % (txid,))
                return False
            self.parse_tx(timestamp, b2lx(bHash), bHeight, tx, wb)

    def db_sync(self):
        self.checktransactions(force=True)
        self.checkaddresses(force=True)
        self.checkblocks(0, force=True)
        gevent.spawn_later(5, self.db_sync)

    def putoneblock(self, block, initsync=True):
        if block.hashPrevBlock != self.gettophash():
            print("Cannot connect block to chain %s %s" % (b2lx(block.GetHash()), b2lx(self.gettophash())))
            return
        height = struct.unpack('i', self.db.get(b'height', struct.pack('i', -1)))[0] + 1
        bHash = b2lx(block.GetHash())
        dt = datetime.utcfromtimestamp(block.nTime)

        if dt > datetime.utcnow() - timedelta(minutes=10) and self.initial_sync:
            self.log.info('Chain has caught up')
            self.initial_sync = False
            self.db_sync()

        with self.db.write_batch(transaction=True) as wb:
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            wb.put(('block:%s' % bHash).encode(), json.dumps({
                'merkle_root': b2lx(block.hashMerkleRoot), # save merkle root as hex string
                'difficulty': block.calc_difficulty(block.nBits), # save difficulty as both calculated and nBits
                'timestamp': timestamp,
                'version': block.nVersion, # we can do binary operation if saved as binary
                'height': height,
                'bits': block.nBits,
                'nonce': block.nNonce,
                'size': len(block.serialize()),
                'hash': bHash,
                'coinbase': str(block.vtx[0].vin[0].scriptSig),
                'tx_count': len(block.vtx),
                'tx': list(map(lambda tx : b2lx(tx.GetHash()), block.vtx))
            }).encode())
            txs = {}
            self.parse_vtx(block.vtx, wb, timestamp, block.GetHash(), height)
            with self.db.write_batch(transaction=True) as addressBatch:
                for key, value in self.address_changes.items():
                    temp = {'address': key, 'balance_change': value}
                    k = ('address:%s' % key).encode()
                    currbal = struct.unpack('l', self.db.get(k, struct.pack('l', 0)))[0]
                    addressBatch.put(k, struct.pack('l', currbal + value))
                    self.address_change_count += 1
            self.address_changes = {}

            self.checktransactions()

            self.checkaddresses()

            self.checkblocks(height)

            h = block.GetHash()
            wb.put(b'tip', h)
            wb.put(b'height', struct.pack('i', height))

            for key, value in self.utxo_cache.items():
                wb.put(key, value)
            self.utxo_cache = {}
            
            self.log.info("UpdateTip: %s height %s" % (b2lx(h), height))
            return dt
        # if not self.have_prevblock(block):
        # 	self.orphans[block.sha256] = True
        # 	self.orphan_deps[block.hashPrevBlock] = block
        # 	self.log.info("Orphan block %064x (%d orphans)" % (block.sha256, len(self.orphan_deps)))
        # 	return False
    def putblock(self, block):
        if self.haveblock(block.GetHash(), True):
            self.log.info("Duplicate block %064x submitted" % (block.GetHash(), ))
            return False
        return self.putoneblock(block)

    def puttxidx(self, txhash, txidx, spend=False, batch=None):
        ser_txhash = int(txhash, 16)
        self.db.get(('tx:'+txhash).encode())
        old_txidx = self.gettxidx(txhash)
        if old_txidx and not spend:
            self.log.warn("overwriting duplicate TX %064x, height %d, oldblk %s, oldspent %x, newblk %s newspent %x" % (ser_txhash, 0, old_txidx.blkhash, old_txidx.spentmask, txidx.blkhash, txidx.spentmask))
        batch = self.db if batch is not None else batch
        value = (txidx.blkhash + ' ' + str(txidx.spentmask)).encode()
        batch.put(('tx:' + txhash).encode(), value)

        return True

    def gettxidx(self, txhash):
        ser_value = self.db.get(('tx:'+txhash).encode())
        if not ser_value:
            return None
        ser_value = ser_value.decode('utf-8')

        pos = ser_value.find(' ')

        txidx = TxIdx(ser_value[:pos])
        # txidx.blkhash = int(, 16)
        txidx.spentmask = int(ser_value[pos+1], 16)

        return txidx

    def spend_txout(self, txhash, n_idx, batch=None):
        txidx = self.gettxidx(txhash)
        if txidx is None:
            return False
        txidx.spentmask |= (1 << n_idx)
        self.puttxidx(txhash, txidx, spend=True, batch=batch)

        return True

    def txout_spent(self, txout):
        txidx = self.gettxidx(b2lx(txout.hash))
        if txidx is None:
            return None

        if txout.n > 100000:	# outpoint index sanity check
            return None

        if txidx.spentmask & (1 << txout.n):
            return True
        return False

    def tx_is_orphan(self, tx):

        for txin in tx.vin:
            rc = self.txout_spent(txin.prevout)
            if rc is None:		# not found: orphan
                try:
                    txfrom = self.mempool.pool[b2lx(txin.prevout.hash)]
                except:
                    return True
                if txin.prevout.n >= len(txfrom.vout):
                    return None
            if rc is True:		# spent? strange
                return None

        return False