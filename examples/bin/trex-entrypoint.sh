#!/usr/bin/env bash
echo "[entrypoint.sh] - Preparing trex_cfg.yaml"

config=$(cat /etc/trex/trex_cfg.yaml)
ips=($(sed -n 's/^\s*-\s*ip\s*:\s*//p' <<< "${config}"))
interfaces=()

for ip in ${ips[@]}; do
    iface=$(ip addr show to ${ip} | sed -n 's/^\w\+:\s*\([0-9a-zA-Z-]\+\)\+.*/\1/p')
    if [ -z "${iface}" ]; then
        echo "[entrypoint.sh] - WARNING: interface matching IP address ${ip} not found!"
    else
        echo "[entrypoint.sh] - Found interface ${iface} matching IP address ${ip}"
        interfaces+=("${iface}")
    fi
done

if [ ${#interfaces[@]} -eq 0 ] && [ ${#ips[@]} -eq 2 ]; then
    echo "[entrypoint.sh] - Didn't found any interfaces matching specified IPs"
    echo "[entrypoint.sh] - Assuming loopback configuration"
    echo "[entrypoint.sh] - Creating and setting up virtual interfaces..."
    interfaces=("veth0" "veth1")
    ip link add ${interfaces[0]} type veth peer name ${interfaces[1]}
    ip a add ${ips[0]}/255.255.255.0 dev ${interfaces[0]}
    ip a add ${ips[1]}/255.255.255.0 dev ${interfaces[1]}
    ip link set dev ${interfaces[0]} up
    ip link set dev ${interfaces[1]} up
    echo "[entrypoint.sh] - Done"
elif [ ${#interfaces[@]} -ne ${#ips[@]} ]; then
    echo "[entrypoint.sh] - Didn't found all interfaces matching specified IPs. Exiting..."
    exit 1
fi

for if_idx in "${!interfaces[@]}"; do
    config=$(sed "s/%IFNAME${if_idx}%/${interfaces[${if_idx}]}/g" <<<"${config}")
done

echo "${config}" >/etc/trex_cfg.yaml

echo "[entrypoint.sh] - /etc/trex_cfg.yaml prepared"
exec "$@"
