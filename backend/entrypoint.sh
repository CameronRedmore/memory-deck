#!/bin/sh
set -e

echo "Container's IP address: `awk 'END{print $1}' /etc/hosts`"

cd /backend/scanmem

./autogen.sh

./configure && make

mkdir -p /backend/out

cp -r /backend/scanmem/.libs/libscanmem.so.1.0.0 /backend/out