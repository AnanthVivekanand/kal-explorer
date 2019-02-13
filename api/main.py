import re
import json
import struct
import uvicorn
import socketio
from redis import Redis
from shared import settings
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

redis = Redis(settings.REDIS_HOST)

class Broadcast(BaseModel):
    data : str

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['GET', 'POST'])

mgr = socketio.AsyncRedisManager('redis://%s' % settings.REDIS_HOST)
sio = socketio.AsyncServer(async_mode='asgi', client_manager=mgr)
#app.add_middleware(socketio.ASGIApp, socketio_server=sio)
app_sio = socketio.ASGIApp(sio, app)
#sio_app = socketio.ASGIApp(sio, app)
#uvicorn.run(sio_app)

from shared.models import Address, Transaction, Block, Utxo
from peewee import RawQuery, fn
from datetime import datetime, timedelta

@sio.on('subscribe')
async def subscribe(sid, room):
    sio.enter_room(sid, room)

pools = {
    'blazepool': {
        'name': 'BlazePool',
        'url': 'http://blazepool.com'
    },
    'zpool.ca': {
        'name': 'Zpool',
        'url': 'https://zpool.ca'
    },
    'zerg': {
        'name': 'Zerg Pool',
        'url': 'http://zergpool.com/'
    },
    'ahashpool': {
        'name': 'A Hash Pool',
        'url': 'https://www.ahashpool.com/'
    },
    'tuxtoke.life': {
        'name': 'Tuxtoke',
        'url': 'http://pool.tuxtoke.life'
    }
}

def get_latest_block():
    return Block.select().order_by(Block.height.desc()).limit(1)[0]

def get_confirmations(height, block=None):
    if height is None:
        return -1
    if block:
        b = block
    else:
        b = get_latest_block()
    return b.height - height

def tx_to_json(tx):
    is_coinbase = (len(tx.vin) == 0)
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
        'addresses_in': tx.addresses_in,
        'addresses_out': tx.addresses_out,
    }

@app.get('/richlist')
def read_richlist(order=None):
    q = Address.select()
    if order == 'sent':
        q = q.order_by(Address.sent.desc())
    elif order == 'received':
        q = q.order_by(Address.received.desc())
    else:
        q = q.order_by(Address.balance.desc())
    res = q.limit(100)
    return list(map(lambda addr : addr.to_dict(), res))

def _utxo_map(block):
    def _func(utxo):
        return {
            'txid': utxo.txid,
            'vout': int(utxo.vout),
            'amount': utxo.amount,
            'scriptPubKey': utxo.scriptPubKey,
            'address': utxo.address,
            'confirmations': get_confirmations(utxo.block_height, block=block),
        }
    return _func

### Address section

@app.get('/addr/{address}/balance')
async def read_address(address : str):
    try:
        record = Address.get(address=address)
    except:
        return HTMLResponse(status_code=404)
    res = record.to_dict()
    unconfirmed = 0
    utxos = Utxo.select().where((Utxo.address == address) & (Utxo.spent == True)).execute()
    for utxo in utxos:
        unconfirmed += utxo.amount
    res['balance'] -= unconfirmed
    res['unconfirmed'] = unconfirmed
    return res

@app.get('/addr/{address}/utxo')
async def read_addr_utxos(address : str):
    utxos = Utxo.select().where((Utxo.address == address) & (Utxo.spent == False))
    #utxos = []
    # check utxo spent?
    #for utxo in _utxos:
    #    q = json.dumps([{'txid': utxo.txid, 'vout': utxo.vout}])
    #    res = Transaction.raw("SELECT * FROM transaction WHERE vin @> %s", q).execute()
    #    if not len(res):
    #        utxos.append(utxo)
    # select * from transaction where vin @> '[{"txid": "016520b9684c95d82111d04257766684ae4a4df45bd7f9b9bdf5648364590053"}]' and block is null
    block = get_latest_block()
    return list(map(_utxo_map(block), utxos))

@app.get('/addrs/{addresses}/utxo')
async def read_addrs_utxo(addresses : str):
    utxos = Utxo.select().where(Utxo.address.in_(addresses.split(',')))
    block = get_latest_block()
    return list(map(_utxo_map(block), utxos))


### Transaction section

@app.get('/tx/{txid}')
def read_tx(txid : str):
    try:
        record = Transaction.get(txid=txid)
    except:
        return HTMLResponse(status_code=404)
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

@app.get('/txs/{address}')
def read_address_txs(address, beforeTime=None):
    val = re.search('^[A-Za-z0-9]+$', address)
    if not val:
        return HTMLResponse(status_code=400)
    if not beforeTime:
        beforeTime = datetime.now().timestamp()

    query = "SELECT * FROM transaction WHERE (addresses_out ? %s OR addresses_in ? %s) AND timestamp < to_timestamp(%s) ORDER BY timestamp DESC LIMIT 10"
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

@app.get('/txs')
def read_block_txs(block : str):
    try:
        b = Block.get(Block.hash == block)
    except Block.DoesNotExist:
        return HTMLResponse(status_code=404)
    res = {
        'txs': []
    }

    txs = Transaction.select().where(Transaction.txid.in_(b.tx))
    block = get_latest_block()
    for tx in txs:
        is_coinbase = (len(tx.vin) == 1 and tx.vin[0]['address'] == None)
        res['txs'].append({
            'blockhash': b.hash,
            'blockheight': b.height,
            'blocktime': int(b.timestamp.timestamp()),
            'confirmations': get_confirmations(b.height, block=block),
            'isCoinBase': is_coinbase,
            'txid': tx.txid,
            'valueOut': tx.output_value,
            'vin': tx.vin,
            'vout': tx.vout,
        })
        return res

### Block section

@app.get('/block/{blockhash}')
def read_blockhash(blockhash):
    try:
        b = Block.get(Block.hash == blockhash)
        prev = Block.get(Block.height == b.height - 1)
    except Block.DoesNotExist:
        return HTMLResponse(status_code=404)
    nxt = None
    try:
        nxt = Block.get(Block.height == b.height + 1)
    except Block.DoesNotExist:
        pass
    # txs = b.tx
    txs = list(Transaction.select().where(Transaction.block == b.hash).execute())

    txs = list(map(lambda tx : {
        'txid': tx.txid,
        'timestamp': int(tx.timestamp.timestamp()),
        'addresses_in': tx.addresses_in,
        'addresses_out': tx.addresses_out
    }, txs))

    def func(a):
        return 1 if 'null' in a['addresses_in'] else 0

    txs.sort(key=func, reverse=True)

    pool = None
    cb = bytes(b.coinbase).decode('utf-8')
    for key, value in pools.items():
        if cb.find(key) != -1:
            pool = value
    
    res = {
        'height': b.height,
        'hash': b.hash,
        'timestamp': int(b.timestamp.timestamp()),
        'merkleroot': b.merkle_root,
        'txs': txs,
        'difficulty': b.difficulty,
        'size': b.size,
        'version_hex': bytes(b.version).hex(),
        'version': struct.unpack('i', bytes(b.version))[0],
        'bits': bytes(b.bits).hex(),
        'nonce': b.nonce,
        'pool': pool,
        'previousblockhash': prev.hash,
    }
    if nxt:
        res['nextblockhash'] = nxt.hash
    return res

@app.get('/blocks')
def read_blocks(beforeBlock=None):
    q = Block.select()
    if beforeBlock:
        q = q.where(Block.height < beforeBlock)
    blocks = q.order_by(Block.timestamp.desc()).limit(100)
    res = []
    for b in blocks:
        pool = None
        cb = bytes(b.coinbase).decode('utf-8')
        for key, value in pools.items():
            if cb.find(key) != -1:
                pool = value
        res.append({
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
            'pool': pool
        })
    return res

### Misc

@app.get('/misc')
def read_misc():
    supply = Address.select(fn.SUM(Address.balance)).execute()[0].sum

    return {
        'supply': int(supply),
    }

# TODO: Probably should cache this method
@app.get('/distribution')
def read_distribution():
    supply = Address.select(fn.SUM(Address.balance)).execute()[0].sum

    res = {}
    sq = Address.select(Address.balance).order_by(Address.balance.desc()).limit(25)
    q = Address.select(fn.SUM(sq.c.balance)).from_(sq)

    res['0_24'] = {
        'percent': (q[0].sum / supply) * 100,
        'total': q[0].sum
    }
    sq = Address.select(Address.balance).order_by(Address.balance.desc()).offset(25).limit(25)
    q = Address.select(fn.SUM(sq.c.balance)).from_(sq)
    res['25_49'] = {
        'percent': (q[0].sum / supply) * 100,
        'total': q[0].sum
    }
    sq = Address.select(Address.balance).order_by(Address.balance.desc()).offset(50).limit(25)
    q = Address.select(fn.SUM(sq.c.balance)).from_(sq)
    res['50_99'] = {
        'percent': (q[0].sum / supply) * 100,
        'total': q[0].sum
    }
    sq = Address.select(Address.balance).order_by(Address.balance.desc()).offset(100)
    q = Address.select(fn.SUM(sq.c.balance)).from_(sq)
    res['remain'] = {
        'percent': (q[0].sum / supply) * 100,
        'total': q[0].sum
    }

    return res

@app.get('/mempool')
def read_mempool():
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

@app.get('/status')
def read_status(q=None):
    if q == 'getInfo':
        latest_block = Block.select().order_by(Block.height.desc()).get()
        mempool_txs = Transaction.select().where(Transaction.block == None).count()
        return {
            'blocks': latest_block.height,
            'lastblockhash': latest_block.hash,
            'difficulty': latest_block.difficulty,
            'mempool_txs': mempool_txs,
        }

@app.post('/broadcast')
def broadcast(data : Broadcast):
    redis.publish('broadcast', data.data)
    return data

# class BroadcastResource(Resource):
#     def put(self):
#         data = request.get_data()

# select address, txid, balance, addresses_out addresses_in from address join transaction  ON addresses_in ? address or addresses_out ? address where address = 'TE2kARbJQrqPG8GfdihzNUYgXxeEg21982' limit 10;
# api.add_resource(RichListResource, '/richlist')
# api.add_resource(AddressResource, '/address/<address>')
# api.add_resource(TransactionResource, '/tx/<txid>')
# api.add_resource(BlockResource, '/block/<blockhash>')
# api.add_resource(BlockListResource, '/blocks')
# api.add_resource(AddressTransactions, '/txs/<address>')
# api.add_resource(BlockTransactions, '/txs')
# api.add_resource(MempoolResource, '/mempool')
# api.add_resource(StatusResource, '/status')
# api.add_resource(BroadcastResource, '/broadcast')

#uvicorn.run(app_sio)
