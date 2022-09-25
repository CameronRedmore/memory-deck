#!/bin/sh
set -e

echo "Container's IP address: `awk 'END{print $1}' /etc/hosts`"

cd /backend

rm -fr scanmem
# Clone scanmem source code
git clone https://github.com/scanmem/scanmem.git

cd /backend/scanmem

./autogen.sh

./configure && make

mkdir -p /backend/out

cp -r /backend/scanmem/.libs/libscanmem.so.1.0.0 /backend/out