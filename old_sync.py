from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from models import *
from datetime import datetime
from fcache.cache import FileCache
import json
import decimal
import os, sys
import queue, threading

utxo_cache = FileCache('garlicoin', flag='c', app_cache_dir=os.getcwd())
# utxo_cache.clear()

q = queue.Queue(maxsize=100)

# rpc_user and rpc_password are set in the bitcoin.conf file
rpc_connection = AuthServiceProxy("http://%s:%s@95.179.202.122:42068"%('user', 'password'))
best_block_hash = rpc_connection.getbestblockhash()
best = rpc_connection.getblock(best_block_hash)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def transaction_worker():
	transactions = []
	changes_list = []
	changes = {}
	utxo_cache_changes = 0
	while True:
		tx = q.get(block=True, timeout=5000)
		for vout in tx['vout']:
			vout['value'] = float(vout['value'])
#		Transaction.create(txid = tx['hash'], vin = tx['vin'], vout = tx['vout'])
		transactions.append({'txid': tx['hash'], 'vin': tx['vin'], 'vout': tx['vout']})
		for vout, data in enumerate(tx['vout']):
			if tx['vout'][vout]['scriptPubKey']['type'] not in ('nonstandard', 'nulldata'):
				utxo_cache['%s:%s' % (tx['hash'], vout)] = {
					'address': tx['vout'][vout]['scriptPubKey']['addresses'][0],
					'value': tx['vout'][vout]['value'],
				}

				utxo_cache_changes += 1
		for vout in tx['vout']:
			if vout['scriptPubKey']['type'] not in ('nonstandard', 'nulldata'):
				address = vout['scriptPubKey']['addresses'][0]
				value = vout['value']
				if address in changes:
					changes[address] += value
				else:
					changes[address] = value

		for vin in tx['vin']:
			if vin.get('coinbase'):
				continue
			vout = vin['vout']
			#pretx = Transaction.get(Transaction.txid == vin['txid'])
			#prevout = pretx.vout
			key = '%s:%s' % (vin['txid'], vout)
			prevout = utxo_cache.pop(key)
			preaddress = prevout['address']
			prevalue = prevout['value']
			if preaddress in changes:
				changes[preaddress] -= prevalue
			else:
				changes[preaddress] = -prevalue

		for key, value in changes.items():
			temp = {'address': key, 'balance_change': value}
			changes_list.append(temp)
		changes = {}
		if len(changes_list) > 3000:
			print('Commiting address balance updates')
			sys.stdout.flush()
			AddressChanges.insert_many(changes_list).execute()
			changes_list = []
			db.execute_sql("insert into address (address, balance) (select address, sum(balance_change) as balance_change from addresschanges group by address) on conflict(address) do update set balance = address.balance + EXCLUDED.balance; TRUNCATE addresschanges;")
		print(len(transactions))
		if len(transactions) > 3000:
			Transaction.insert_many(transactions).execute()
			print('Commiting transactions')
			sys.stdout.flush()
			transactions = []
		if utxo_cache_changes > 1000:
			print('Syncing utxo cache to disk')
			sys.stdout.flush()
			utxo_cache_changes = 0
			utxo_cache.sync()


def parse_txs(block):
	txchunks = chunks(block["tx"], 10)
	txs = []
	for chunk in txchunks:
		# print('RPC start')
		# print(chunk)
		# sys.stdout.flush()
		txs = txs + (rpc_connection.batch_([["getrawtransaction", txs, True ] for txs in chunk]))
		# print('RPC done')
		# print(txs)
		# sys.stdout.flush()
	for tx in txs:
		# print(tx)
		q.put(tx, block=True)


def run():
	t = threading.Thread(target=transaction_worker, args=())
	t.daemon = True
	t.start()
	cblocks = chunks(range(int(best['height'])), 100)

	for x_heights in cblocks:
		commands = [ [ "getblockhash", height ] for height in x_heights ]
		block_hashes = rpc_connection.batch_(commands)
		blocks = rpc_connection.batch_([ [ "getblock", h ] for h in block_hashes ])

		bs = []
		for block in blocks:
			print("Processing block %s" % block['height'])
			bs.append({
				'height': block['height'],
				'hash': block['hash'],
				'timestamp': datetime.utcfromtimestamp(block['time']).strftime('%Y-%m-%d %H:%M:%S'),
				'difficulty': block['difficulty'],
				'merkle_root': block['merkleroot']
			})
			if block['height'] > 0:
				parse_txs(block)
	#	break
	#	Block.insert_many(bs).execute()
		print("Completed %s (utxo_cache size %s queue %s) " % (x_heights, len(utxo_cache), q.qsize()))
	t.join()
if __name__ == "__main__":
	run()
