import os
import bitcointx
import importlib

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_PORT = os.getenv('DB_PORT', 5432)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
NODE_IP    = os.getenv('COIN_DAEMON', '45.77.228.139')

EXP_COIN = os.getenv('COIN', 'tux')
module = importlib.import_module("shared.coins.%s" % EXP_COIN)
ChainParams = module.ChainParams

DB_NAME = 'explorer_%s' % EXP_COIN

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
