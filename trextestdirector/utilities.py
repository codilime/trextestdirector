import collections
import json
import logging
import logging.config
import os.path
import socket
import time
from collections import defaultdict

import yaml

from trextestdirector.errors import TrexTestDirectorConfigError

logger = logging.getLogger(__name__)

_server_config_optional_values = {
    "async_port": 4500,
    "sync_port": 4501,
}

_port_optional_values = {"service_mode": False, "attributes": {}}

_test_config_optional_values = {
    "name": "untitled_test",
    "duration": -1,
    "iterations": 1,
}

_default_logging_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"default": {"format": "%(name)s - %(levelname)s - %(message)s"},},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"],},
}


def is_reachable(ip, port, timeout=1, max_retries=10, retry_interval=2):
    """Check whether server is reachable or not."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    for try_count in range(max_retries + 1):
        try:
            s.connect((ip, port))
        except socket.error as error:
            logger.info(f"{ip}:{port} is not reachable: {error}")
            logger.info("Retrying...")
            time.sleep(retry_interval)
        else:
            logger.info(f"{ip}:{port} is reachable")
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            return True
    logger.error(f"Couldn't reach {ip}:{port} after {try_count} retries")
    return False


def load_config(path):
    """Load config from YAML or JSON file."""
    config = None
    extension = os.path.splitext(path)[1]
    try:
        with open(path, "rt") as config_file:
            if extension == ".yaml":
                config = yaml.safe_load(config_file)
            elif extension == ".json":
                config = json.load(config_file)
            else:
                error_msg = f"Unknown file extension: {extension}"
                logger.error(error_msg)
                raise TrexTestDirectorConfigError(error_msg)
            logger.info(f"Config loaded from {path}")
    except IOError as e:
        logger.error(f"Config file {path} was not found")
        raise e
    except Exception as e:
        logger.error("Unhandled exception", exc_info=e)
        raise e
    if not config:
        raise TrexTestDirectorConfigError("Config file is empty")
    return config


def update_config(config):
    """Update default config with user's values."""
    if config.get("servers"):
        for server_idx, server in enumerate(config["servers"]):
            server = {**_server_config_optional_values, **server}
            ports = server["ports"]
            for port_idx, port in enumerate(ports):
                port = {**_port_optional_values, **port}
                ports[port_idx] = port
            server["ports"] = ports
            config["servers"][server_idx] = server
    if config.get("tests"):
        for test_idx, test in enumerate(config["tests"]):
            test = {**_test_config_optional_values, **test}
            config["tests"][test_idx] = test


def validate_servers_config(servers_config):
    """Validate 'servers' part of configuration file."""
    if not servers_config or len(servers_config) < 1:
        raise TrexTestDirectorConfigError(
            "Missing required 'servers' field in configuration file."
        )
    server_required_fields = ["management_ip", "async_port", "sync_port", "ports"]
    port_required_fields = ["id", "ip", "default_gateway"]
    server_names = set()
    for server in servers_config:
        server_name = server["name"]
        if server_name in server_names:
            msg = f"{server_name}: name {server_name} is used multiple times."
            raise TrexTestDirectorConfigError(msg)
        server_names.add(server_name)
        for field in server_required_fields:
            if field not in server:
                msg = f"{server_name}: missing required field {field} in the configuration."
                raise TrexTestDirectorConfigError(msg)
        for port in server["ports"]:
            for field in port_required_fields:
                if field not in port:
                    msg = f"{server_name}: missing required field {field} port {port['id']} configuration."
                    raise TrexTestDirectorConfigError(msg)


def validate_tests_config(tests_config, servers_config):
    """Validate 'tests' part of configuration file."""
    # Define required test config fields to validate
    test_required_fields = ["transmit"]
    transmit_required_fields = ["from", "to"]
    # Collect server names and port ids from servers configuration
    servers = {}
    for server_config in servers_config:
        servers[server_config["name"]] = [port["id"] for port in server_config["ports"]]
    logger.debug(f"servers = {servers}")
    # Validate test configuration fields and values
    test_names = set()
    for test in tests_config:
        test_name = test["name"]
        if test_name in test_names:
            msg = f"{test_name}: test name {test_name} is used multiple times."
            raise TrexTestDirectorConfigError(msg)
        test_names.add(test_name)
        for field in test_required_fields:
            if field not in test:
                msg = f"{test_name}: missing required field {field} in configuration."
                raise TrexTestDirectorConfigError(msg)
        for tx_config in test["transmit"]:
            for field in transmit_required_fields:
                if field not in tx_config:
                    msg = (
                        f"{test_name}: missing required field {field} in configuration."
                    )
                    raise TrexTestDirectorConfigError(msg)
            tx_server_name, tx_port_id = tx_config["from"].split(":")
            rx_server_name, rx_port_id = tx_config["to"].split(":")
            if (
                tx_server_name not in servers
                or int(tx_port_id) not in servers[tx_server_name]
            ):
                msg = f"{test_name}: server {tx_server_name} port {tx_port_id} is not defined in servers configuration."
                raise TrexTestDirectorConfigError(msg)
            if (
                rx_server_name not in servers
                or int(rx_port_id) not in servers[rx_server_name]
            ):
                msg = f"{test_name}: server {rx_server_name} port {rx_port_id} is not defined in servers configuration."
                raise TrexTestDirectorConfigError(msg)


def validate_config(config):
    """Check if config has defined required fields."""
    validate_servers_config(config["servers"])
    validate_tests_config(config["tests"], config["servers"])


def set_up_logging(path):
    """Set up logging configuration."""
    if path and os.path.exists(path):
        with open(path, "rt") as yaml_file:
            log_config = yaml.safe_load(yaml_file)
        logging.config.dictConfig(log_config)
    else:
        logging.config.dictConfig(_default_logging_config)
        logging.info("Using default logging configuration")


def format_num(size, unit="", compact=True):
    txt = "NaN"

    if type(size) == str:
        return "N/A"

    prefix = ""
    if compact:
        for prefix in ["", "K", "M", "G", "T", "P"]:
            if abs(size) < 1000.0:
                break
            size /= 1000.0

    if isinstance(size, float):
        if compact:
            txt = "{:.2f}".format(size)
        else:
            txt = "{:3.2f}".format(size)
    else:
        txt = "{}".format(size)

    if prefix or unit:
        txt += " {:}{:}".format(prefix, unit)
    return txt


def save_results_to_file(stats, file_name):
    with open(file_name, "w+") as file_handler:
        json.dump(stats, file_handler, indent=2)
