import os

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST', '172.17.0.2')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
