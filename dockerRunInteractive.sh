#!/bin/bash
docker run --privileged --cap-drop=all --name rta_container --rm -it rta:latest bash
