import os

from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'postgres')