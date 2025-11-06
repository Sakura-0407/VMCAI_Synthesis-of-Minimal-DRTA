#!/bin/bash
docker build --build-arg USERID=$(id -u) -t rta:latest -f docker/Dockerfile .
