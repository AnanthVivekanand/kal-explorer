#!/bin/bash -x

docker run -d \
	--name postgres \
	-v postgres:/var/lib/postgresql/data \
	-p 127.0.0.1:5432:5432 \
	postgres:11