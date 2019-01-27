import re
import struct
from flask import Flask, abort
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

from models import Address, Transaction, Block
from peewee import RawQuery
from datetime import datetime, timedelta
from webargs import fields, validate
from webargs.flaskparser import use_kwargs, parser

def get_confirmations(height):
    if height is None:
        return -1
    b = Block.select().order_by(Block.height.desc()).limit(1)[0]
    return b.height - height

def tx_to_json(tx):
    is_coinbase = (len(tx.vin) == 1 and tx.vin[0]['address'] == None)
    return {
        'blockhash': tx.block,
        'blockheight': tx.block_height,
        'timestamp': int(tx.timestamp.timestamp()),
        'confirmations': get_confirmations(tx.block_height),
        'isCoinBase': is_coinbase,
        'txid': tx.txid,
        'valueOut': tx.output_value,
        'vin': tx.addresses_in,
        'vout': tx.addresses_out,
    }

class AddressResource(Resource):
    def get(self, address):
        try:
            record = Address.get(address=address)
        except:
            abort(404)
        return {
            '_satoshis': record.balance,
            'balance': record.balance / 100000000
        }

class TransactionResource(Resource):
    def get(self, txid):
        try:
            record = Transaction.get(txid=txid)
        except:
            abort(404)
        fee = record.input_value - record.output_value
        if fee < 0:
            fee = 0 # probably coinbase tx
        return {
            'txid': record.txid,
            'block': record.block,
            'timestamp': record.timestamp.timestamp(),
            'input_value': record.input_value,
            'output_value': record.output_value,
            'fee': fee,
            'addresses_in': record.addresses_in,
            'addresses_out': record.addresses_out,
        }

class AddressTransactions(Resource):
    # TODO: Add beforeTime and limit filters
    args = {
        'beforeTime': fields.Int()
    }
    @use_kwargs(args)
    def get(self, address, beforeTime=None):
        val = re.search('^[A-Za-z0-9]+$', address)
        if not val:
            abort(400)
        if not beforeTime:
            beforeTime = datetime.now().timestamp()

        query = "SELECT * FROM transaction WHERE (addresses_out ? %s OR addresses_in ? %s) AND timestamp < to_timestamp(%s) ORDER BY timestamp DESC LIMIT 100"
        txs = Transaction.raw(query, address, address, beforeTime)

        txs = list(map(lambda tx: tx_to_json(tx), txs))
        if len(txs) == 0:
            lastTime = None
        else:
            lastTime = txs[-1]['timestamp']
        res = {
            'count': len(txs),
            'lastTime': lastTime,
            'txs': txs,
        }
        return res


class BlockTransactions(Resource):
    args = {
        'block': fields.Str(
            required=True,
        ),
    }

    @use_kwargs(args)
    def get(self, block):
        try:
            b = Block.get(Block.hash == block)
        except Block.DoesNotExist:
            abort(404)
        res = {
            'txs': []
        }

        txs = Transaction.select().where(Transaction.txid.in_(b.tx))
        for tx in txs:
            is_coinbase = (len(tx.vin) == 1 and tx.vin[0]['address'] == None)
            res['txs'].append({
                'blockhash': b.hash,
                'blockheight': b.height,
                'blocktime': int(b.timestamp.timestamp()),
                'confirmations': get_confirmations(b.height),
                'isCoinBase': is_coinbase,
                'txid': tx.txid,
                'valueOut': tx.output_value,
                'vin': tx.vin,
                'vout': tx.vout,
            })
        return res

class BlockResource(Resource):
    def get(self, blockhash):
        try:
            b = Block.get(Block.hash == blockhash)
            prev = Block.get(Block.height == b.height - 1)
        except Block.DoesNotExist:
            abort(404)
        nxt = None
        try:
            nxt = Block.get(Block.height == b.height + 1)
        except Block.DoesNotExist:
            pass
        
        res = {
            'height': b.height,
            'hash': b.hash,
            'timestamp': int(b.timestamp.timestamp()),
            'merkleroot': b.merkle_root,
            'tx': b.tx,
            'difficulty': b.difficulty,
            'size': b.size,
            'version_hex': bytes(b.version).hex(),
            'version': struct.unpack('i', bytes(b.version))[0],
            'bits': bytes(b.bits).hex(),
            'nonce': b.nonce,
            'previousblockhash': prev.hash,
        }
        if nxt:
            res['nextblockhash'] = nxt.hash
        return res

class BlockListResource(Resource):
    args = {
        'beforeBlock': fields.Int()
    }
    @use_kwargs(args)
    def get(self, beforeBlock=None):
        q = Block.select()
        if beforeBlock:
            q = q.where(Block.height < beforeBlock)
        blocks = q.order_by(Block.timestamp.desc()).limit(100)
        print(bytes(blocks[0].version).hex())
        res = map(lambda b : {
            'height': b.height,
            'hash': b.hash,
            'timestamp': int(b.timestamp.timestamp()),
            'merkle_root': b.merkle_root,
            'tx': b.tx,
            'difficulty': b.difficulty,
            'size': b.size,
            'version_hex': bytes(b.version).hex(),
            'version': struct.unpack('i', bytes(b.version))[0],
            'bits': bytes(b.bits).hex(),
            'nonce': b.nonce,
            # 'coinbase': b.coinbase,
        }, blocks)
        return list(res)

class MempoolResource(Resource):
    def get(self):
        txs = Transaction.select().where(Transaction.block == None)
        data = []
        for record in txs:
            fee = record.input_value - record.output_value
            if fee < 0:
                fee = 0 # probably coinbase tx
            data.append({
                'txid': record.txid,
                'block': record.block,
                'timestamp': record.timestamp.timestamp(),
                'input_value': record.input_value,
                'output_value': record.output_value,
                'fee': fee,
                'addresses_in': record.addresses_in,
                'addresses_out': record.addresses_out,
            })
        return data

class StatusResource(Resource):
    args = {
        'q': fields.Str(
            required=False,
            validate=validate.OneOf(['getInfo']),
        ),
    }
    @use_kwargs(args)
    def get(self, q=None):
        if q == 'getInfo':
            latest_block = Block.select().order_by(Block.height.desc()).get()
            return {
                'blocks': latest_block.height,
                'lastblockhash': latest_block.hash,
                'difficulty': latest_block.difficulty,
            }


# select address, txid, balance, addresses_out addresses_in from address join transaction  ON addresses_in ? address or addresses_out ? address where address = 'TE2kARbJQrqPG8GfdihzNUYgXxeEg21982' limit 10;
api.add_resource(AddressResource, '/address/<address>')
api.add_resource(TransactionResource, '/tx/<txid>')
api.add_resource(BlockResource, '/block/<blockhash>')
api.add_resource(BlockListResource, '/blocks')
api.add_resource(AddressTransactions, '/txs/<address>')
api.add_resource(BlockTransactions, '/txs')
api.add_resource(MempoolResource, '/mempool')
api.add_resource(StatusResource, '/status')
