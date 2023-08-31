#!/bin/bash

ACTION=$1
SOURCE_NAME=$2
SWAGGER_PORT=${2:-8080}

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

serve () {
    echo "Swagger UI running at http://localhost:$SWAGGER_PORT"
    docker run --rm -p $SWAGGER_PORT:8080 -v $PWD/api/openapi.v1.yaml:/tmp/openapi.v1.yaml -e SWAGGER_JSON=/tmp/openapi.v1.yaml swaggerapi/swagger-ui:v5.4.2
}

develop () {
    echo "Swagger Editor running at http://localhost:$SWAGGER_PORT"
    docker run --rm -p $SWAGGER_PORT:8080 -v $PWD/api/openapi.v1.yaml:/tmp/openapi.v1.yaml -e SWAGGER_FILE=/tmp/openapi.v1.yaml swaggerapi/swagger-editor:v4-latest
}

case $ACTION in
    build)
        build
        ;;
    generate)
        generate
        ;;
    serve)
        serve
        ;;
    develop)
        develop
        ;;
    *)
        echo "Usage: $0 [build | generate | develop] [YYYYMMDD | PORT]"
        echo "Examples:"
        echo "-  $0 build             # Build the Docker image"
        echo "-  $0 generate          # Generate all resources listed in sources.json file"
        echo "-  $0 generate 20230101 # Generate 20230101 resources only"
        echo "-  $0 develop           # Run Swagger Editor on port 8080 (default)"
        echo "-  $0 develop 8081      # Run Swagger Editor on port 8081 (custom)"
        ;;
esac
