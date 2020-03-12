# TRex Test Director scenarios

TRex Test Director scenario is a custom test which can be run using TRex Test Director. Only one test scenario can be defined in Python file.

Test scenario class must inherits from `TrexStlScenario` class and implement `test` method which accepts only one parameter `self`.

In implementation of `test` method following member variables can be used:

- `self.clients`: A list of clients connected to TRex servers based on provided configuration file.
- `self.servers`: A list of dictionaries containing following keys:
  - `name`: Server name.
  - `client`: A client connected to the server.
  - `ports`: A list of ports extracted from server's part of the configuration file.
- `tests`: A list of tests defined in configuration file.
- `test_config`: Current test configuration.
- `statistics`: A dictionary of statistics for each test, where test names are keys.
- `get_server_by_ip(ip)`: A member function which returns server dictionary based on provided IP.
- `get_port_by_ip(ip)`: A member function which returns port configuration based on provided IP
- `get_server_by_name(name)`: A member function which returns server dictionary.
- `get_port_by_id(server_name, id)`: A member function which returns dictionary with port configuration based on provided server name and port id.
- `print_test_results(servers)`: A member function which prints test results on standard output for provided list of servers.
- `start_traffic(servers, wait_for_traffic)`: A member function which starts traffic for provided list of servers.
