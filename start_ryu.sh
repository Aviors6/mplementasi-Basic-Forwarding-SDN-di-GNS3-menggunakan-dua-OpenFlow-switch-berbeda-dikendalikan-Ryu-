#!/bin/sh
ip addr add 10.10.10.10/24 dev eth0 2>/dev/null
ip link set eth0 up
pkill -f ryu-manager
sleep 1
ryu-manager --ofp-tcp-listen-port 6633 /root/ryu_basic_forwarding_of10.py
