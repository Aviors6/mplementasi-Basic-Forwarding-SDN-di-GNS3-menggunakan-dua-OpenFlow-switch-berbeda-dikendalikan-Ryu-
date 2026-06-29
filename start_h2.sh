#!/bin/sh
ip link set eth0 up
ip addr add 10.0.0.2/24 dev eth0 2>/dev/null
arp -s 10.0.0.1 0c:48:12:37:00:02
echo "H2 ready: $(ip addr show eth0 | grep 'inet ')"
arp -n
