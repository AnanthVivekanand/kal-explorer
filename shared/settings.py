import os
import bitcointx

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST', '172.17.0.2')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
COIN = 100000000
NODE_IP = '45.77.228.139'

class CoreChainParams(bitcointx.core.CoreChainParams):
    MAX_MONEY = None
    GENESIS_BLOCK = None
    PROOF_OF_WORK_LIMIT = None
    SUBSIDY_HALVING_INTERVAL = None
    NAME = None

class ChainParams(CoreChainParams):
    MAX_MONEY = 69000000 * COIN
    GENESIS_BLOCK = None # currently not needed
    PROOF_OF_WORK_LIMIT = None # currently not needed
    SUBSIDY_HALVING_INTERVAL = None # currently not needed
    NAME = None # currently not needed
    RPC_PORT = 42072
    PORT = 42071
    NETMAGIC = b'\xfc\xc5\xbf\xda'
    BASE58_PREFIXES = {
        'PUBKEY_ADDR':65,
        'SCRIPT_ADDR':64,
        'SECRET_KEY' :193,
        'EXTENDED_PUBKEY': b'\x04\x88\xb2\x1e',
        'EXTENDED_PRIVKEY': b'\x04\x88\xad\xe4'
    }
    BECH32_HRP = 'tux'

POOLS = {
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