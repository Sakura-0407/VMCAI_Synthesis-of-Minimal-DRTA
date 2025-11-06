#!/bin/bash
docker run --privileged --cap-drop=all --volume="`pwd`/results:/home/ubuntu/results:Z" --rm -t rta:latest bash -c "./runExperimentDocker.sh $@ rti.xml"
