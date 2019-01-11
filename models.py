from peewee import *
from playhouse.postgres_ext import BinaryJSONField

db = PostgresqlDatabase('garlicoin', user='postgres', password='postgres', host='localhost', port=5432)

class BaseModel(Model):
	class Meta:
		database = db

class Block(BaseModel):
	height = IntegerField(unique=True)
	hash = CharField(max_length=64, unique=True)
	timestamp = DateTimeField()
	merkle_root = CharField(max_length=64, unique=True)
	difficulty = FloatField()
	size = IntegerField()
	version = BlobField()
	bits = BlobField()
	nonce = BigIntegerField()
	coinbase = BlobField()

class Transaction(BaseModel):
	txid = CharField(max_length=64, unique=True, index=True)
	vin = BinaryJSONField()
	vout = BinaryJSONField()

class AddressChanges(BaseModel):
	address = TextField(index=True)
	balance_change = BigIntegerField()

class Address(BaseModel):
	address = TextField(unique=True, index=True)
	balance = BigIntegerField()

db.connect()
db.create_tables([Block, Transaction, Address, AddressChanges])
