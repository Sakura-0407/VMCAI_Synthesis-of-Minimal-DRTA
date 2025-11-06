#!/bin/bash
file=`echo $1 | sed s/py/csv/`
./FlexFringe-main/build/flexfringe --ini FlexFringe-main/ini/rti.ini $file && gc -ne $file.ff.final.dot
