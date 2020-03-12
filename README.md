# TRex Test Director

## What is TRex Test Director

TRex Test Director is a simple tool created to faciliate writing and running simple, customizable performance tests between two or more TRex instances. TRex Test Director is designed to work with TRex running in **stateless** mode.

TRex Test Director requires Python 3.6 or higher.

## What is TRex

Via [TRex homepage](https://trex-tgn.cisco.com/): "TRex is an open source, low cost, stateful and stateless traffic generator fuelled by DPDK. It generates L4-7 traffic based on pre-processing and smart replay of real traffic templates . TRex amplifies both client and server side traffic and can scale up to 200Gb/sec with one UCS.

TRex Stateless functionality includes support for multiple streams, the ability to change any packet field and provides per stream statistics, latency and jitter.

Advanced Stateful functionality includes support for emulating L7 traffic with fully-featured scalable TCP layer.
".

### Codilime's TRex fork

At Codilime we implemented [PTP](https://en.wikipedia.org/wiki/Precision_Time_Protocol) support for better latency measurements. For details see [Codilime's TRex fork wiki](https://github.com/codilime/trex-core/wiki).

### How to install and run TRex

For details how to install Codilime's TRex with PTP support see [Codilime's Trex fork wiki](https://github.com/codilime/trex-core/wiki/Installation).

For details how to install original TRex see [TRex wiki](https://github.com/cisco-system-traffic-generator/trex-core/wiki) and [manual](https://trex-tgn.cisco.com/trex/doc/trex_manual.html).

For quick start we recommend to use Docker and docker-compose: you will only need to download [(Codilime's) TRex source code](https://github.com/codilime/trex-core) or [(original) TRex source code](https://github.com/cisco-system-traffic-generator/trex-core).

Alternatively you can download [TRex release package](https://trex-tgn.cisco.com/trex/release/) and unpack it.

### How to instal land run TRex Test Director

Assuming you downloaded TRex source code or downloaded and unpacked TRex release package you need to add TRex's `interactive` directory to your `PYTHONPATH`:

- if you downloaded TRex source code:

    ```bash
    export PYTHONPATH=$PYTHONPATH:<trex_source_code_directory>/scripts/automation/trex_control_plane/interactive
    ```

- if you downloaded and unpacked TRex release package:

    ```bash
    export PYTHONPATH=$PYTHONPATH:<trex_release_package_directory>/automation/trex_control_plane/interactive
    ```

Then you can download [trex_test_scenario](https://github.com/codilime/trextestdirector) and install it using PIP:

```bash
pip3 install .
```

### Repository structure

- `trextestdirector`: contains Python package for writing traffic profiles and test scenarios. `trextestdirector` module is also used to run test scenarios.

- `examples`: contains examples of docker-compose files, test configurations and traffic profiles.

- `docs`: contains markdown documents with documentation.

## Usage

```bash
python3 -m trex_test_scenario [-h] [-s SCENARIO] [-l LOG_CONFIG] [-o OUTPUT_FILE] config
```

### Test configuration

For details of creating test configuration files see [appropriate doc](docs/test_configs.md).

### Traffic profiles

For details of creating traffic profiles see [appropriate doc](docs/traffic_profiles.md).

### Test scenarios

For details of creating test scenarios see [appropriate doc](docs/test_scenarios.md).

## docker-compose examples

### Prerequisites

1. [docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/).
2. [docker-compose](https://docs.docker.com/compose/install/).

### Single TRex server (loopback configuration)

In this example one TRex server will be run using docker-compose.

1. Run docker-compose with `docker-compose-loopback.yml`:

    ```bash
    docker-compose -f docker-compose-loopback.yml up --build
    ```

2. Start another terminal and run TRex Test Director with default scenario:

    ```bash
    python3 -m trex_test_scenario configs/loopback.yaml
    ```

3. Remove containers and networks:

    ```bash
    docker-compose -f docker-compose-loopback.yml down
    ```

### Two TRex servers (transmitter->receiver configuration)

In this example two containers with TRex servers will be run using docker-compose. One of the servers will start traffic and the other one will receive the traffic.

1. Run docker-compose with `docker-compose-2-servers.yml`

    ```bash
    docker-compose -f docker-compose-2-servers.yml
    ```

2. Start another terminal and run test scenario

    ```bash
    python3 -m trex_test_scenario configs/2-servers.yaml
    ```

3. Remove containers and networks:

    ```bash
    docker-compose -f docker-compose-2-servers.yml down
    ```

### Two TRex servers and SUT (transmitter->SUT->receiver configuration)

In this example two container with TRex servers and one with Ubuntu 19.04 will be run using docker-compose. Ubuntu will be simulating SUT (System Under Test) by forwarding traffic received from one TRex to the other one.

1. Run docker-compose with `docker-compose-sut.yml`:

    ```bash
    docker-compose -f docker-compose-sut.yml
    ```

2. Start another terminal and run test scenario

    ```bash
    python3 -m trex_test_scenario configs/sut.yaml
    ```

3. Remove containers and networks:

    ```bash
    docker-compose -f docker-compose-sut.yml down
    ```
