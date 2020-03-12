import ast
import json
import logging
import os
import os.path
import signal
import sys
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from pydoc import locate

from trex.common.trex_exceptions import TRexError
from trex.stl.api import (
    STLClient,
    STLFlowLatencyStats,
    STLFlowStats,
    STLProfile,
    STLStream,
    STLTXCont,
)
from trex.utils import text_tables
from trextestdirector.utilities import is_reachable, update_config, validate_config
from trextestdirector.stats_printer import print_port_stats, print_latency_stats
from trextestdirector.errors import TrexTestDirectorInterruptError

logger = logging.getLogger(__name__)


class TrexStlScenario(ABC):
    """Base class for TRex STL mode test scenarios."""

    def __init__(self, config):
        update_config(config)
        validate_config(config)
        self.clients = []
        self.servers = []
        self.tests = config["tests"]
        self.test_config = None
        self.statistics = {}
        self._server_by_name = {}
        self._server_by_ip = {}
        self._port_by_ip = {}

        for test_config in self.tests:
            test_name = test_config["name"]
            self.statistics[test_name] = {}
            for iteration in range(1, test_config["iterations"] + 1):
                self.statistics[test_name][iteration] = {}

        for server_config in config["servers"]:
            server_name = server_config["name"]
            server_ip = server_config["management_ip"]
            sync_port = server_config["sync_port"]
            async_port = server_config["async_port"]
            client = STLClient(
                server=server_ip,
                sync_port=sync_port,
                async_port=async_port,
                verbose_level="error",
            )
            ports = server_config["ports"]
            server = {"name": server_name, "client": client, "ports": ports}
            for port in ports:
                port_ip = port["ip"]
                self._port_by_ip[port_ip] = port
                self._server_by_ip[port_ip] = server
            self.clients.append(client)
            self.servers.append(server)
            self._server_by_name[server_name] = server

    def _connect_clients(self):
        """Connect clients to servers defined in loaded configuration."""

        for server in self.servers:
            server_name = server["name"]
            client = server["client"]
            server_ip = client.ctx.server
            sync_port = client.ctx.sync_port
            logger.debug(f"{server_name}: connecting to {server_ip}:{sync_port}")
            if not is_reachable(server_ip, sync_port):
                error_msg = f"{server_name}: cannot connect to {server_ip}:{sync_port}"
                logger.error(error_msg)
                raise Exception(error_msg)
            client.connect()

    def _disconnect_clients(self):
        """Disconnect all clients."""

        for client in self.clients:
            try:
                client.reset()
            except TRexError as e:
                logger.error(e)
            try:
                client.release()
            except TRexError as e:
                logger.error(e)
            if client.is_connected():
                try:
                    client.disconnect()
                except TRexError as e:
                    logger.error(e)

    def _set_up_servers(self):
        """Set up servers based on loaded configuration."""
        for server in self.servers:
            server_name = server["name"]
            client = server["client"]
            port_ids = [port["id"] for port in server["ports"]]
            logger.debug(f"{server_name}: acquiring and resetting ports {port_ids}...")
            client.reset(port_ids)
            logger.debug(f"{server_name}: ports {port_ids} acquired")
            client.set_service_mode(port_ids)
            for port in server["ports"]:
                port_id = port["id"]
                port_ip = port["ip"]
                default_gateway = port["default_gateway"]
                logger.debug(f"{server_name}: setting up port {port_id}")
                logger.debug(
                    f"{server_name}: port {port_id} set to l3 mode: src_ipv4 = {port_ip}, dst_ipv4 = {default_gateway}"
                )
                client.set_l3_mode(port_id, port_ip, default_gateway)
                service_mode = port.get("service_mode")
                if service_mode:
                    logger.debug(f"{server_name}: port {port_id} set to service mode")
                else:
                    client.set_service_mode(port_id, enabled=False)
                attributes = port.get("attributes")
                if attributes:
                    client.set_port_attr(port_id, **attributes)
                    logger.debug(
                        f"{server_name}: port {port_id} attributes set: {attributes}"
                    )
            client.clear_stats(port_ids)

    def _set_up_test(self, test):
        """Set up test."""
        for client in self.clients:
            client.stop()
            client.remove_all_streams()
            client.remove_rx_queue()
        test["iteration"] = 0
        self.test_config = test
        self._load_traffic_profiles(test)

    def _load_traffic_profiles(self, test_config):
        """Load traffic profiles for all ports based on loaded configuration."""
        test_name = test_config["name"]
        logger.debug(f"{test_name}: loading traffic profiles")
        for tx_config in test_config["transmit"]:
            tx_server_name, tx_port_id = tx_config["from"].split(":")
            rx_server_name, rx_port_id = tx_config["to"].split(":")
            tx_port_ip = self.get_port_by_id(tx_server_name, tx_port_id)["ip"]
            rx_port_ip = self.get_port_by_id(rx_server_name, rx_port_id)["ip"]
            tunables = {
                **{"src_ip": tx_port_ip, "dst_ip": rx_port_ip},
                **tx_config.get("tunables", {}),
            }
            profile_file = tx_config.get("profile_file")
            if not profile_file:
                logger.info(
                    f"{test_name}: profile file for {tx_server_name} port {tx_port_id} is not defined. Using default profile"
                )
                profile_file = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "default_profile.py",
                )
            client = self.get_server_by_name(tx_server_name)["client"]
            profile = STLProfile.load(profile_file, port_id=tx_port_id, **tunables)
            stream_ids = client.add_streams(profile.get_streams(), tx_port_id)
            stream_ids = stream_ids if isinstance(stream_ids, list) else [stream_ids]
            logger.debug(
                f"Added {len(stream_ids)} streams to {tx_server_name} port {tx_port_id}"
            )
            # to measure stats we need to attach to the receiver
            # a stream with pg_id of transmitter's stats stream, because
            # (see: https://trex-tgn.cisco.com/trex/doc/trex_faq.html
            # section 1.5.15.: "latency streams are handled by rx software")
            flow_stats_type = tunables.get("flow_stats")
            if flow_stats_type:
                if flow_stats_type not in ("stats", "latency"):
                    raise Exception(
                        'Unknown stats type. Valid values: "stats", "latency"'
                    )
                pg_id = tunables.get(
                    "flow_stats_pg_id", tunables.get("flow_stats_pg_id")
                )
                if not pg_id:
                    raise Exception("Streams with flow stats must have defined pg_id")
                if rx_server_name == tx_server_name:
                    continue
                if flow_stats_type == "latency":
                    flow_stats = STLFlowLatencyStats(pg_id=pg_id)
                else:
                    flow_stats = STLFlowStats(pg_id=pg_id)
                flow_stats_stream = STLStream(flow_stats=flow_stats, start_paused=True)
                flow_stats_profile = STLProfile(flow_stats_stream)
                rx_server_client = self.get_server_by_name(rx_server_name)["client"]
                stream_ids = rx_server_client.add_streams(
                    flow_stats_profile.get_streams(), rx_port_id
                )
                stream_ids = (
                    stream_ids if isinstance(stream_ids, list) else [stream_ids]
                )
                logger.debug(
                    f"{test_name}: Added {len(stream_ids)} streams to {rx_server_name} port {rx_port_id}"
                )
        logger.debug(f"{test_name}: traffic profiles succesfully loaded")

    def _set_up(self):
        """Connect clients and set up servers."""
        self._register_sigint_handler()
        self._connect_clients()
        self._set_up_servers()

    def _tear_down(self):
        """Clean up after test."""
        for client in self.clients:
            client.stop()
        self._disconnect_clients()

    def _sigint_handler(self, sig, frame):
        logger.debug(f"Received SIGINT. Aborting test...")
        self.print_test_results()
        raise TrexTestDirectorInterruptError

    def _register_sigint_handler(self):
        signal.signal(signal.SIGINT, self._sigint_handler)

    #
    #   API
    #

    @staticmethod
    def load_trex_test_scenario(python_file):
        """Load a Trex test scenario from Python file."""
        if not os.path.isfile(python_file):
            raise Exception(f"File {python_file} does not exist")

        basedir = os.path.dirname(python_file)
        sys.path.insert(0, basedir)

        with open(python_file) as file_handler:
            node = ast.parse(file_handler.read())
        class_defs = [n for n in node.body if isinstance(n, ast.ClassDef)]
        class_candidates = []
        for class_def in class_defs:
            if any(
                base_class.id == "TrexStlScenario" for base_class in class_def.bases
            ):
                class_candidates.append(class_def)
        logger.debug(f"test scenario class candidates: {class_candidates}")
        if len(class_candidates) < 1:
            raise Exception(f"Didn't found any test scenarios in {python_file}")
        if len(class_candidates) > 1:
            raise Exception(f"{python_file} contains more than one test scenario.")
        class_name = class_candidates[0].name
        dont_write_bytecode = sys.dont_write_bytecode
        file_name = os.path.basename(python_file).split(".")[0]
        try:
            sys.dont_write_bytecode = True
            TrexTest = locate(f"{file_name}.{class_name}", 1)
            if not TrexTest:
                raise Exception(
                    f"Failed to load Trex test scenario from {python_file}."
                )
            return TrexTest
        except Exception as e:
            logger.error("Unhandled exception", exc_info=e)
            raise e
        finally:
            sys.dont_write_bytecode = dont_write_bytecode
            sys.path.remove(basedir)

    def get_server_by_ip(self, ip):
        return self._server_by_ip[ip]

    def get_port_by_ip(self, ip):
        return self._port_by_ip[ip]

    def get_server_by_name(self, name):
        return self._server_by_name[name]

    def get_port_by_id(self, server_name, port_id):
        server = self._server_by_name[server_name]
        port = next(
            (port for port in server["ports"] if port["id"] == int(port_id)), None,
        )
        if not port:
            error_msg = f"Cannot found server {server_name} port {port_id} in servers configuration"
            logger.error(error_msg)
            raise Exception(error_msg)

        return port

    def print_test_results(self, servers=None):
        """Print TRex stats for each server."""
        servers = servers if servers else self.servers
        for server in servers:
            server_name = server["name"]
            server_header = f"Stats summary for {server_name}"
            print("-" * len(server_header))
            print(server_header)
            print("-" * len(server_header))
            print_port_stats(server)
            print_latency_stats(server)

    def start_traffic(self, servers=None, wait_for_traffic=True):
        servers = servers if servers else self.servers
        for server in servers:
            server_name = server["name"]
            client = server["client"]
            port_to_run_ids = []
            for port in server["ports"]:
                port_id = port["id"]
                port_streams = client.get_port(port_id).get_all_streams()
                if port_streams:
                    port_to_run_ids.append(port_id)
            # We only need to start all ports with streams
            if port_to_run_ids:
                logger.debug(
                    f"{server_name}: starting traffic on ports: {port_to_run_ids}"
                )
                client.start(
                    ports=port_to_run_ids,
                    duration=self.test_config["duration"],
                    force=True,
                )
        if wait_for_traffic:
            for server in self.servers:
                client = server["client"]
                client.wait_on_traffic()

    def run(self):
        """Set up, perform and tear down test."""
        self._set_up()
        for test_config in self.tests:
            self._set_up_test(test_config)
            test_name = test_config["name"]
            for iteration in range(1, int(test_config["iterations"]) + 1):
                print(f"Starting test {test_name}: iteration {iteration}")
                self.test()
                for server in self.servers:
                    server_name = server["name"]
                    stats = server["client"].get_stats()
                    self.statistics[test_name][iteration][server_name] = stats
                print(f"Test {test_name}: iteration {iteration} finished")
                print(f"Results for test {test_name}: iteration {iteration}")
                self.print_test_results()
        self._tear_down()

    @abstractmethod
    def test(self):
        """This method should implement test procedure."""
