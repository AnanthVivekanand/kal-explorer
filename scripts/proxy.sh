#!/bin/bash

name=proxy

docker rm -f proxy
docker run -d --name proxy \
	-e DOMAINS=tuxcoin.wildgarlic.fun \
	-e EMAIL=ryan@rshaw.me \
	-v letsencrypt:/etc/letsencrypt \
	-v cronstamps:/var/spool/cron/cronstamps \
	-p 80:80 -p 443:443 \
	--link explorer:www \
	--network explorer \
	-e STAGING=false \
	ryanshaw/haproxy-letsencrypt
