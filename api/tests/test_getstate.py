import pytest

from starlette.testclient import TestClient
from peewee import PostgresqlDatabase
from shared.models import Block
from api.main import app

client = TestClient(app)
# test_db = Po(':memory:')
test_db = PostgresqlDatabase('test_db', user='postgres', password='postgres', host='localhost', port=5432)
MODELS = [Block]

@pytest.fixture(scope="session")
def db():
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(MODELS)
    yield
    test_db.drop_tables(MODELS)

@pytest.fixture(scope="session")
def block(db):
    Block.create(**{
        'height': 0,
        'hash': 'cf7938a048f1442dd34f87ce56d3e25455b22a44f676325f1ae8c7a33d0731c7',
        'timestamp': '2018-06-17 00:50:36',
        'merkle_root': '3ead103523ad8f9bfc8365c7b5ddb6f10c731c6274730e88bcaa2c74606dd4bb',
        'tx': ["3ead103523ad8f9bfc8365c7b5ddb6f10c731c6274730e88bcaa2c74606dd4bb"],
        'difficulty': 0.000244141,
        'size': 286,
        'nonce': 2085541870,
        'version': b'01000000',
        'bits': b'f0ff0f1e',
        'coinbase': b'04ffff001d0104464e6f727468204b6f7265616e2066696c6d206f6e204b696d27732053696e6761706f726520747269702072657665616c73206e657720666f637573206f6e2065636f6e6f6d79',
        'tx_count': 1
    })

def test_getInfo(block):
    res = client.get('/status?q=getInfo')
    assert res.json() == {'blocks': 0, 'lastblockhash': 'cf7938a048f1442dd34f87ce56d3e25455b22a44f676325f1ae8c7a33d0731c7', 'difficulty': 0.000244141, 'mempool_txs': 0}

def test_getDifficulty(block):   
    res = client.get('/status?q=getDifficulty')
    assert res.json() == {'difficulty': 0.000244141}

def test_getBestBlockHash(block):
    res = client.get('/status?q=getBestBlockHash')
    assert res.json() == {'bestblockhash': 'cf7938a048f1442dd34f87ce56d3e25455b22a44f676325f1ae8c7a33d0731c7'}

def test_getLastBlockHash(block):
    res = client.get('/status?q=getLastBlockHash')
    assert res.json() == {'syncTipHash': 'cf7938a048f1442dd34f87ce56d3e25455b22a44f676325f1ae8c7a33d0731c7', 'lastblockhash': 'cf7938a048f1442dd34f87ce56d3e25455b22a44f676325f1ae8c7a33d0731c7'}