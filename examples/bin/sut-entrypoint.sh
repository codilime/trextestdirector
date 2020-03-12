#!/usr/bin/env bash
set -e
apt-get update && apt-get install -y iproute2

tc qdisc add dev eth0 root netem delay 100ms
echo 1 > /proc/sys/net/ipv4/ip_forward
tail -f /dev/null