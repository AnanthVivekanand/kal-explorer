
import gevent
import string
import struct
import os, sys
import bitcoin
import binascii
import io
import json
import threading
from datetime import datetime
from cache import Cache
from models import *

from bitcoin.messages import msg_block
from bitcoin.core import b2lx, lx, uint256_from_str, CBlock
from bitcoin.core.serialize import uint256_from_str, uint256_to_str, uint256_from_compact
from bitcoin.wallet import CBitcoinAddress
from bitcoin.core.script import CScript
from bitcointx.wallet import CBitcoinAddress as TX_CBitcoinAddress
from datetime import datetime, timedelta

def int_to_bytes(i: int, *, signed: bool = False) -> bytes:
    length = (i.bit_length() + 7 + int(signed)) // 8
    return i.to_bytes(length, byteorder='big', signed=signed)

def bytes_to_int(b: bytes, *, signed: bool = False) -> int:
    return int.from_bytes(b, byteorder='big', signed=signed)

def ser_uint256(i):
    return uint256_to_str(i)

class TxIdx(object):
    def __init__(self, blkhash, spentmask=0):
        self.blkhash = blkhash
        self.spentmask = spentmask

class BlkMeta(object):
    def __init__(self):
        self.height = -1
        self.work = 0

    def deserialize(self, s):
        s = s.decode('utf-8')
        l = s.split()
        if len(l) < 2:
            raise RuntimeError
        self.height = int(l[0])
        self.work = int(l[1], 16)

    def serialize(self):
        r = str(self.height) + ' ' + hex(self.work)
        return r.encode()

    def __repr__(self):
        return "BlkMeta(height %d, work %x)" % (self.height, self.work)


class HeightIdx(object):
    def __init__(self):
        self.blocks = []

    def deserialize(self, s):
        s = s.decode('utf-8')
        self.blocks = []
        l = s.split()
        for hashstr in l:
            hash = lx(hashstr)
            self.blocks.append(hash)

    def serialize(self):
        l = []
        for blkhash in self.blocks:
            l.append(b2lx(blkhash))
        return (' '.join(l)).encode()

    def __repr__(self):
        return "HeightIdx(blocks=%s)" % (self.serialize(),)

class ChainDb(object):

    def __init__(self, log, mempool, params):
        self.log = log
        self.mempool = mempool
        self.params = params
        self.utxo_changes = 0
        self.cache = Cache()
        self.cache.clear()

        ## level DB 
        #    pg_block: block data to insert into PG database
        #    pg_tx:    transaction data to insert into PG database
        #    tx:*      transaction outputs
        #    misc:*    state
        #    height:*  list of blocks at height h
        #    blkmeta:* block metadata
        #    blocks:*  block seek point in stream
        datadir = './data'
        self.db = self.cache.db
        self.blk_write = io.BufferedWriter(io.FileIO(datadir + '/blocks.dat','ab'))
        self.blk_read = io.BufferedReader(io.FileIO(datadir + '/blocks.dat','rb'))

        if self.db.get(b'misc:height') is None:
            self.log.info('INITIALIZING EMPTY BLOCKCHAIN DATABASE')
            with self.db.write_batch(transaction=True) as batch:
                batch.put(b'misc:height', struct.pack('i', -1))
                batch.put(b'misc:msg_start', self.params.NETMAGIC)
                batch.put(b'misc:tophash', ser_uint256(0))
                batch.put(b'misc:total_work', b'0x0')

        start = self.db.get(b'misc:msg_start')
        if start != self.params.NETMAGIC:
            self.log.error("Database magic number mismatch. Data corruption or incorrect network?")
            raise RuntimeError


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
        return self.db.get(b'misc:tophash')

    def haveblock(self, sha256, _):
        return False

    def getheight(self):
        d = self.db.get(b'misc:height')
        return struct.unpack('i', d)[0]

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
                        for key, value in sn.iterator(prefix=b'pg_tx:'):
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
                for key, value in self.db.iterator(prefix=b'pg_block:'):
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
        if batch:
            # TODO: remove old utxo db
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
            batch.put(('pg_tx:%s' % txid).encode(), json.dumps(tx_data).encode())
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

    def clear_txout(self, txhash, n_idx, batch=None):
        txidx = self.gettxidx(txhash)
        if txidx is None:
            return False

        txidx.spentmask &= ~(1 << n_idx)
        self.puttxidx(txhash, txidx, batch)

        return True

    def unique_outputs(self, block):
        outputs = {}
        txmap = {}
        for tx in block.vtx:
            if tx.is_coinbase:
                continue
            txmap[tx.GetHash()] = tx
            for txin in tx.vin:
                v = (txin.prevout.hash, txin.prevout.n)
                if v in outputs:
                    return None

                outputs[v] = False

        return (outputs, txmap)

    def db_sync(self):
        self.checktransactions(force=True)
        self.checkaddresses(force=True)
        self.checkblocks(0, force=True)
        gevent.spawn_later(5, self.db_sync)

    def putoneblock(self, block, initsync=True):
        if block.hashPrevBlock != self.gettophash():
            print("Cannot connect block to chain %s %s" % (b2lx(block.GetHash()), b2lx(self.gettophash())))
            return

        top_height = self.getheight()
        top_work = bytes_to_int(self.db.get(b'misc:total_work'))

        prevmeta = BlkMeta()
        if top_height >= 0:
            ser_prevhash = b2lx(block.hashPrevBlock)
            data = self.db.get(('blkmeta:'+ser_prevhash).encode())
            prevmeta.deserialize(data)
        else:
            ser_prevhash = ''

        # build network "block" msg, as canonical disk storage form
        msg = msg_block()
        msg.block = block
        msg_data = msg.to_bytes()

        # write "block" msg to storage
        fpos = self.blk_write.tell()
        self.blk_write.write(msg_data)
        self.blk_write.flush()

        batch = self.db.write_batch(transaction=True)
        
        with self.db.write_batch(transaction=True) as batch:

            # add index entry
            ser_hash = b2lx(block.GetHash())
            batch.put(('blocks:'+ser_hash).encode(), int_to_bytes(fpos))

            # store metadata related to this block
            blkmeta = BlkMeta()
            blkmeta.height = prevmeta.height + 1
            blkmeta.work = (prevmeta.work +
                    uint256_from_compact(block.nBits))
            batch.put(('blkmeta:'+ser_hash).encode(), blkmeta.serialize())

            # store list of blocks at this height
            heightidx = HeightIdx()
            heightstr = str(blkmeta.height)
            d = self.db.get(('height:'+heightstr).encode())
            if d:
                heightidx.deserialize(d)
            heightidx.blocks.append(block.GetHash())

            batch.put(('height:'+heightstr).encode(), heightidx.serialize())

        # print('height: %s' % blkmeta.height)
        # print('blk: %s' % blkmeta.work)
        # print('top: %s' % top_work)

        # if chain is not best chain, proceed no further
        if (blkmeta.work <= top_work):
            self.log.info("ChainDb: height %d (weak), block %s" % (blkmeta.height, b2lx(block.GetHash())))
            return True

        # update global chain pointers
        if not self.set_best_chain(ser_prevhash, ser_hash, block, blkmeta):
            return False

        return True

    def set_best_chain(self, ser_prevhash, ser_hash, block, blkmeta):
        # the easy case, extending current best chain
        if (blkmeta.height == 0 or b2lx(self.db.get(b'misc:tophash')) == ser_prevhash):
            c = self.connect_block(ser_hash, block, blkmeta)
            if blkmeta.height > 0:
                self.disconnect_block(block)
            return c

        # switching from current chain to another, stronger chain
        return self.reorganize(block.GetHash())

    def getblockmeta(self, blkhash):
        ser_hash = b2lx(blkhash)
        try:
            meta = BlkMeta()
            meta.deserialize(self.db.get(('blkmeta:'+ser_hash).encode()))
        except KeyError:
            return None

        return meta
    
    def getblockheight(self, blkhash):
        meta = self.getblockmeta(blkhash)
        if meta is None:
            return -1

        return meta.height

    def reorganize(self, new_best_blkhash):
        self.log.warn("REORGANIZE")

        conn = []
        disconn = []

        old_best_blkhash = self.gettophash()
        fork = old_best_blkhash
        longer = new_best_blkhash
        while fork != longer:
            while (self.getblockheight(longer) > self.getblockheight(fork)):
                block = self.getblock(longer)
                block.calc_sha256()
                conn.append(block)

                longer = block.hashPrevBlock
                if longer == 0:
                    return False

            if fork == longer:
                break

            block = self.getblock(fork)
            disconn.append(block)

            fork = block.hashPrevBlock
            if fork == 0:
                return False

        self.log.warn("REORG disconnecting top hash %064x" % (old_best_blkhash,))
        self.log.warn("REORG connecting new top hash %064x" % (new_best_blkhash,))
        self.log.warn("REORG chain union point %064x" % (fork,))
        self.log.warn("REORG disconnecting %d blocks, connecting %d blocks" % (len(disconn), len(conn)))

        for block in disconn:
            if not self.disconnect_block(block):
                return False

        for block in conn:
            if not self.connect_block(b2lx(block.GetHash()), block, self.getblockmeta(block.GetHash())):
                return False

        self.log.warn("REORGANIZE DONE")
        return True

    def disconnect_block(self, block):
        ser_prevhash = b2lx(block.hashPrevBlock)
        prevmeta = BlkMeta()
        prevmeta.deserialize(self.db.get(('blkmeta:'+ser_prevhash).encode()))

        tup = self.unique_outputs(block)
        if tup is None:
            return False

        outputs = tup[0]

        # mark deps as unspent
        with self.db.write_batch(transaction=True) as batch:
            for output in outputs:
                self.clear_txout(output[0], output[1], batch)

            # update tx index and memory pool
            for tx in block.vtx:
                ser_hash = b2lx(tx.GetHash())
                batch.delete(('tx:'+ser_hash).encode())

                if not tx.is_coinbase():
                    self.mempool_add(tx)

            # update database pointers for best chain
            batch.put(b'misc:total_work', int_to_bytes(prevmeta.work))
            batch.put(b'misc:height', struct.pack('i', prevmeta.height))
            batch.put(b'misc:tophash', lx(ser_prevhash))

            self.log.info("ChainDb(disconn): height %d, block %s" % (prevmeta.height, b2lx(block.hashPrevBlock)))

        return True

    def connect_block(self, ser_hash, block, blkmeta):

        # update database pointers for best chain
        with self.db.write_batch(transaction=True) as wb:
            wb.put(b'misc:total_work', int_to_bytes(blkmeta.work))
            wb.put(b'misc:height', struct.pack('i', blkmeta.height))
            wb.put(b'misc:tophash', lx(ser_hash))

            self.log.info("ChainDb: height %d, block %s" % (blkmeta.height, b2lx(block.GetHash())))

            bHash = b2lx(block.GetHash())
            dt = datetime.utcfromtimestamp(block.nTime)

            if dt > datetime.utcnow() - timedelta(minutes=10) and self.initial_sync:
                self.log.info('Chain has caught up')
                self.initial_sync = False
                self.db_sync()

            height = blkmeta.height
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            wb.put(('pg_block:%s' % bHash).encode(), json.dumps({
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
            # wb.put(b'tip', h)
            # wb.put(b'height', struct.pack('i', height))

            for key, value in self.utxo_cache.items():
                wb.put(key, value)
            self.utxo_cache = {}
            
            # self.log.info("UpdateTip: %s height %s" % (b2lx(h), height))
            return dt

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

    def getblock(self, blkhash):
        # block = self.blk_cache.get(blkhash)
        # if block is not None:
        #     return block

        ser_hash = ser_uint256(blkhash)
        try:
            # Lookup the block index, seek in the file
            fpos = int(self.db.get(('blocks:'+ser_hash).encode()))
            self.blk_read.seek(fpos)

            # read and decode "block" msg
            msg = CBlock.stream_deserialize(self.blk_read)
            if msg is None:
                return None
            block = msg.block
        except KeyError:
            return None

        # self.blk_cache.put(blkhash, block)

        return block

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