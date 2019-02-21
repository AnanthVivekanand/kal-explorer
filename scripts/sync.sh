#!/bin/bash

docker run --name sync -d \
	-e SYNC_ONLY=true \
	--network explorer \
	--entrypoint=/usr/local/bin/python \
	-e DB_HOST=postgres \
	-e REDIS_HOST=redis \
	-v /data/explorer:/data/explorer \
	explorer \
	sync.py
