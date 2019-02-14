import os

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST', '172.17.0.2')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')

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
