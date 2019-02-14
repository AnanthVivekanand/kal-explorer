# Kryptonite explorer
!! Currently under development !!

An open source explorer with support for UTXO based crypto-currencies.

## Contributions
Contributions are welcomed, encouraged and may be rewarded with [Tuxcoin](https://tuxcoin.io) (The open source software coin). 

## Getting started

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

This project uses (pipenv)[https://github.com/pypa/pipenv] for its dependencies, installing the dependencies for the API/sync server can be done using `pipenv sync` in the root. The dependencies for the UI in `ui/` can be installed using `npm install`.

## Frontend
`ng serve --open`

## API
`pipenv run uvicorn api.main:app_sio --debug`

## Sync daemon
`pipenv run python sync.py`

## Donate

BTC: 3MAMXxzzdLy9NQqBvQebnrZjZjQJRC4HTD