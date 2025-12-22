#!/bin/bash

make ppa_sign || exit 1

for versionName in precise trusty xenial bionic; do
    for retryCount in 1 2 3 4 5 6 7 8 9 10; do
	make ppa_${1}_$versionName && break
	sleep 20
    done
    # Actually wrong, if wee succeeded on the 10th try...
    if [ "$retryCount" = "10" ]; then
	exit 1
    fi
done
