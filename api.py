import struct
from flask import Flask, abort
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

from models import Address, Transaction, Block
from datetime import datetime, timedelta
from webargs import fields, validate
from webargs.flaskparser import use_kwargs, parser

def get_confirmations(height):
    b = Block.select().order_by(Block.height.desc()).limit(1)[0]
    return b.height - height

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
            coinbase = (len(tx.vin) == 1 and tx.vin[0]['address'] == None)
            res['txs'].append({
                'blockhash': b.hash,
                'blockheight': b.height,
                'blocktime': int(b.timestamp.timestamp()),
                'confirmations': get_confirmations(b.height),
                'isCoinBase': True,
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
    def get(self):
        blocks = Block.select().order_by(Block.timestamp.desc()).limit(10)
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
api.add_resource(BlockTransactions, '/txs')
api.add_resource(MempoolResource, '/mempool')
api.add_resource(StatusResource, '/status')
