#!/bin/bash

ACTION=$1
SOURCE_NAME=$2

NGINX_PORT=${2:-8080}
SWAGGER_UI_PORT=8091
SWAGGER_ED_PORT=8092

DOCKER_IMAGE_NAME=ondata-conf-amm-istat
DOCKER_IMAGE_VERSION=latest
DOCKER_IMAGE=$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_VERSION
DOCKER_VOLUME=$PWD:/app

NGINX_VERSION=latest
SWAGGER_UI_VERSION=v5.4.2
SWAGGER_ED_VERSION=v4-latest

build () {
    docker build --target application -t $DOCKER_IMAGE_NAME .
}

generate () {
    if [ -z "$SOURCE_NAME" ]; then
        docker run --rm -v $DOCKER_VOLUME $DOCKER_IMAGE
    else
        docker run --rm -e SOURCE_NAME=$SOURCE_NAME -v $DOCKER_VOLUME $DOCKER_IMAGE
    fi
}

serve () {
    echo "API served at http://localhost:$NGINX_PORT"
    docker run --rm -p $NGINX_PORT:80 -v $PWD/nginx.conf:/etc/nginx/conf.d/default.conf -v $PWD/api:/usr/share/nginx/html:ro nginx:$NGINX_VERSION
    echo "Shutdown API"
}

swagger_ui () {
    echo "Swagger UI running at http://localhost:$SWAGGER_UI_PORT"
    docker run --rm -p $SWAGGER_UI_PORT:8080 -v $PWD/api/openapi.v1.yaml:/tmp/openapi.v1.yaml -e SWAGGER_JSON=/tmp/openapi.v1.yaml swaggerapi/swagger-ui:$SWAGGER_UI_VERSION
    echo "Shutdown Swagger UI"
}

swagger_ed () {
    echo "Swagger Editor running at http://localhost:$SWAGGER_ED_PORT"
    docker run --rm -p $SWAGGER_ED_PORT:8080 -v $PWD/api/openapi.v1.yaml:/tmp/openapi.v1.yaml -e SWAGGER_FILE=/tmp/openapi.v1.yaml swaggerapi/swagger-editor:$SWAGGER_ED_VERSION
    echo "Shutdown Swagger Editor"
}

documentation () {
    (trap 'kill 0' SIGINT; swagger_ui & swagger_ed)
}

deploy () {
    git push origin `git subtree split --prefix api main`:gh-pages --force
}

shell () {
    docker run --rm -it -v $DOCKER_VOLUME --entrypoint /bin/bash $DOCKER_IMAGE
}

lint () {
    poetry run pre-commit run --files main.py
}

help () {
    echo "Usage: $0 [build | generate | serve | documentation] [YYYYMMDD | PORT]"
    echo "Examples:"
    echo "- $0 build              # Build the Docker image"
    echo "- $0 generate           # Generate all resources listed in sources.json file"
    echo "- $0 generate 20230101  # Generate a custom resource only"
    echo "- $0 serve              # Serve API on port $NGINX_PORT (default)"
    echo "- $0 serve 8081         # Serve API on custom port"
    echo "- $0 documentation      # Run Swagger UI on port $SWAGGER_UI_PORT and Swagger Editor on port $SWAGGER_ED_PORT"    
    echo "You can exit the running process with ctrl+c"
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
    documentation)
        documentation
        ;;
    deploy)
        deploy
        ;;
    shell)
        shell
        ;;
    lint)
        lint
        ;;
    help)
        help
        ;;
    *)
        echo "Error, wrong syntax!"
        help
        ;;
esac
