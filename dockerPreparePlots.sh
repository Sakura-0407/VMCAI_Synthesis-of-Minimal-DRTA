#!/bin/bash
docker run --privileged --cap-drop=all --volume="`pwd`/results:/home/ubuntu/results:Z" --volume="`pwd`/plots:/home/ubuntu/plots:Z" --rm -t rta:latest bash -c "./preparePlots.sh"
