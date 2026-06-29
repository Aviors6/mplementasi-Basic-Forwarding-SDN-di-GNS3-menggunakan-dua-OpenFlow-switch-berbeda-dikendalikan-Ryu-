#!/bin/sh
ip addr add 10.10.10.1/24 dev eth0 2>/dev/null
ip link set eth0 up
ovs-vsctl del-br br0 2>/dev/null
ovs-vsctl add-br br0
ovs-vsctl set bridge br0 other-config:datapath-id=0000000000000001
ovs-vsctl set bridge br0 protocols=OpenFlow10
ovs-vsctl set-fail-mode br0 secure
ovs-vsctl add-port br0 eth1 -- set interface eth1 ofport_request=1
ovs-vsctl add-port br0 eth2 -- set interface eth2 ofport_request=2
ovs-vsctl set-controller br0 tcp:10.10.10.10:6633
echo "OVS ready"
ovs-vsctl show
