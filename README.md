# Kal explorer
:exclamation: :exclamation: Currently under development :exclamation: :exclamation:

An open source explorer/wallet with support for UTXO based crypto-currencies.

## Contributions 
Contributions are welcomed, encouraged and may be rewarded with [Tuxcoin](https://tuxcoin.io) (The open source software coin). 

## Getting started :school_satchel:

This getting started section assumes you have docker installed.

### Setup coin daemon
Install your coin daemon of choice and make sure it is fully synced with the network.

### Setup docker env
Create network:
```
docker network create explorer
```

Pull & run postgres
```
docker run -d \
	--name postgres \
	-v postgres:/var/lib/postgresql/data \
	timescale/timescaledb:latest-pg11
```

Pull & run redis:
```
docker run -d --name redis --network explorer redis
```

Create explorer
```
docker build -t explorer .

docker run -d \
	--name explorer \
	-e DB_HOST=postgres \
	-e REDIS_HOST=redis \
	--network explorer \
	explorer

```

Start a reverse proxy with https
```
docker run -d --name proxy \
	-e DOMAINS=<domain> \
	-e EMAIL=<email> \
	-v letsencrypt:/etc/letsencrypt \
	-v cronstamps:/var/spool/cron/cronstamps \
	-p 80:80 -p 443:443 \
	--link explorer:www \
	--network explorer \
	-e STAGING=false \
	ryanshaw/haproxy-letsencrypt
```

## Data directories

PostgreSQL and LevelDB is used for this explorer. 

PostgreSQL provides analytical capabilities and is what powers the frontend and APIs. LevelDB is needed to track chainstate such as UTXOs and spent values, LevelDB as it is much faster than PostgreSQL.

## Development

This project uses [pipenv](https://github.com/pypa/pipenv) for its dependencies, installing the dependencies for the API/sync server can be done using `pipenv sync` in the root. The dependencies for the UI in `ui/` can be installed using `npm install`.

### Frontend
`ng serve --open`

### API
`pipenv run uvicorn api.main:app_sio --debug`

### Sync daemon
`pipenv run python sync.py`

# Donate

This project is not funded by anyone and is maintained and developed in my free time, if this project helps you please consider donating.

TUX: tux1qcc00c3m5xadczfnklgpsgksxwpnu0dk8q5mhha

BTC: 38XCv6WkzpXQWugnuyCuEXPHyzxFgEtVkx

ETH: 0xDA0e3423c8E721cA2D00e625EdfBb7db29012b90

XRP: rphkRxHMh8gMc2o7aFLoEEWWbQeCSWcLYb

XLM: GALCRW7AXDA4ANVCL2DAQ7XQ3HQDL2H5GKN7KAKHTQHFEHG7AFZE2R6S

<a href="https://www.buymeacoffee.com/HklE8Fn" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
