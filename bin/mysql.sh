#!/bin/bash

set -e

CONTAINER_NAME=sample-mysql

function usage() {
cat >&2 <<EOF
ログ:
docker logs -f $CONTAINER_NAME


ログインコマンド:
MYSQL_PWD=root1234 mysql -u root -h 127.0.0.1 -P 3306

MYSQL_PWD=pass1234 mysql -u app -h 127.0.0.1 -P 3306
EOF
exit 1
}

args=()
while [ "$1" != "" ]; do
  case $1 in
    -h | --help ) usage ;;
    *           ) args+=("$1") ;;
  esac
  shift
done



# DockerHub: https://hub.docker.com/_/mysql
docker rm -f $CONTAINER_NAME || true
docker run \
  --rm \
  -d \
  --name $CONTAINER_NAME \
  -e MYSQL_ROOT_PASSWORD=root1234 \
  -e MYSQL_DATABASE=sample \
  -e MYSQL_USER=app \
  -e MYSQL_PASSWORD=pass1234 \
  -p 3306:3306 \
  mysql:8.4 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

docker logs -f $CONTAINER_NAME