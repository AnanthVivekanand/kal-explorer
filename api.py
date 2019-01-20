import struct
from flask import Flask, abort
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

from models import Address, Transaction, Block
from datetime import datetime, timedelta

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

# select address, txid, balance, addresses_out addresses_in from address join transaction  ON addresses_in ? address or addresses_out ? address where address = 'TE2kARbJQrqPG8GfdihzNUYgXxeEg21982' limit 10;
api.add_resource(AddressResource, '/address/<address>')
api.add_resource(TransactionResource, '/tx/<txid>')
api.add_resource(BlockListResource, '/blocks')
api.add_resource(MempoolResource, '/mempool')