import os

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST', '172.17.0.2')