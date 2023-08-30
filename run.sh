#!/bin/bash

ACTION=$1
SOURCE_NAME=$2

DOCKER_IMAGE_NAME=ondata-conf-amm-istat
DOCKER_IMAGE_VERSION=latest
DOCKER_IMAGE=$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_VERSION
DOCKER_VOLUME=$PWD:/app

build() {
    docker build --target application -t $DOCKER_IMAGE_NAME .
}

generate() {
    if [ -z "$SOURCE_NAME" ]; then
        docker run --rm -v $DOCKER_VOLUME $DOCKER_IMAGE
    else
        docker run --rm -e SOURCE_NAME=$SOURCE_NAME -v $DOCKER_VOLUME $DOCKER_IMAGE
    fi
}

case $ACTION in
    build)
        build
        ;;
    generate)
        generate
        ;;
    *)
        echo "Usage: $0 [build | generate] [YYYYMMDD]"
        ;;
esac
