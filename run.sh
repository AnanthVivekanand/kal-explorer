#!/bin/bash

docker build -t explorer .
docker stop explorer
docker rm -f explorer

docker run --rm -v $(pwd)/chainstate:/usr/src/app/chainstate explorer