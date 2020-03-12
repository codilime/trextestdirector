# TRex Test Director configuration files

## Configuration file

```yaml
servers:
  - name: side_a
    management_ip: 10.0.100.10
    sync_port: 4501
    async_port: 4500
    ports:
      - id: 0
        ip: 192.168.100.10
        default_gateway: 192.168.100.20
        service_mode: true
        attributes:
          promiscuous: true
      - id: 1
        ip: 172.16.100.10
        default_gateway: 172.16.100.20
        service_mode: true
        attributes:
          promiscuous: true

  - name: side_b
    management_ip: 10.0.100.20
    sync_port: 4501
    async_port: 4500
    ports:
      - id: 0
        ip: 192.168.100.20
        default_gateway: 192.168.100.10
        service_mode: true
        attributes:
          promiscuous: true
      - id: 1
        ip: 192.168.100.20
        default_gateway: 172.16.100.10
        service_mode: true
        attributes:
          promiscuous: true

tests:
  - name: latency_test
    duration: 30
    iterations: 1
    transmit:
      - from: side_b:0
        to: side_a:0
        profile_file: traffic_profiles/latency_profile.py
        tunables:
          pps: 10000
          flow_stats: latency
          flow_stats_pps: 100
          flow_stats_pg_id: 11
      - from: side_b:1
        to: side_a:1
        profile_file: traffic_profiles/latency_profile.py
        tunables:
          pps: 10000
          flow_stats: latency
          flow_stats_pps: 100
          flow_stats_pg_id: 12
```

Configuration file is divided into two sections: `servers` section and `tests` section.

The `servers` section is a list of TRex servers with all details required by TRex client to connect to the server.

The `tests` section is a list of test's parameters and traffic configuration which can be used in test scenarios.

- `servers`: Required list of server details used to create and connect TRex clients.
  - `name`: Required string value defining the server's name, which will be used in `test` section to define direction of traffic.
  - `management_ip`: Required value defining IP address of TRex server.
  - `sync_port`: Optional integer value defining sync port of TRex server. If not provided the default value 4501 is used.
  - `async_ports`: Optional integer value defining async port of TRex server. If not provided the default value 4500 is used.
  - `ports`: Required list of TRex ports. Each port is a map containing port details.
    - `id`: Required integer value defining port's ID. Must be consistent with port's position defined in TRex configuration file,
    - `ip`: Required value defining port's IP. Must be consistent with port's `ip` defined in TRex configuration file,
    - `default_gateway`: Required value defining port's default gateway. Must be consistent with port's `default_gw` defined in TRex configuration file.
    - `service_mode`: Optional flag (defaults false) to control whether or not client should set the port to service mode,
    - `attributes`: Optional map of port attributes (see [port attributes](https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/client_code.html#trex.stl.trex_stl_client.STLClient.set_port_attr))
- `tests`: Required list of test details.
  - `name`: Required string value defining test's name.
  - `duration`: Optional integer value (defaults to -1, which is interpreted as infinite duration) defining duration of the test.
  - `iterations`: Optional integer value (defaults to 1) defining number of test's iterations.
  - `transmit`: Required map of values defining traffic details.
    - `from`: Two required values separated by colon defining transmitter (source of traffic). The first value is name of TRex server, the second one is port of that server.
    - `to`: Two required values separated by colon defining receiver (destination of traffic). The first value is name of TRex server, the second one is port of that server.
    - `profile_file`: Optional value defining path to traffic profile file. If not provided the default traffic profile is used.
    - `tunables`: Optional map of parameters used to tune traffic properties. Important note: allowed values are defined in profile file.
      - `pps`: Optional value used in default traffic profile defining rate of sending packets (packets per second).
      - `flow_stats`: Optional value (defaults to `null`) used in default traffic profile defining type of statistics. Allowed values are `null`, `stats` and `latency`.
      - `flow_stats_pps`: Optional value used in default traffic profile defining rate of latency packets.
      - `flow_stats_pg_id`: If `flow_stats` is not set as `null` it is required value defining packet group ID used for statistics. Must be unique.
