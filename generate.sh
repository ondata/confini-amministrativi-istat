#!/bin/bash
#docker run -e SOURCE_NAME=$1 -v $PWD/sources.json:/app/sources.json -v $PWD/v1:/app/output ondata-conf-amm-istat:latest
docker run -e SOURCE_NAME=$1 -v $PWD:/app ondata-conf-amm-istat:latest
