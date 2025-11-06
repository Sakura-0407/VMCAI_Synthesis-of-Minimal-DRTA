#!/bin/bash
benchexec --read-only-dir / --overlay-dir /home --maxLogfileSize=-1 --no-container $@
