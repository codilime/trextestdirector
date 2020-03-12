#!/usr/bin/env bash
set -e

ip link add veth0 type veth peer name veth1
ip a add 198.18.10.10/255.255.255.0 dev veth0
ip a add 198.18.20.10/255.255.255.0 dev veth1
ip link set dev veth0 up
ip link set dev veth1 up

exec "$@"