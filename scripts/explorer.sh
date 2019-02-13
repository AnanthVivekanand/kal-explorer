#!/bin/bash
docker build -t explorer .
docker stop explorer
docker rm explorer
docker run -d --name explorer -e DB_HOST=postgres --network explorer \
	-e REDIS_HOST=redis \
	explorer
