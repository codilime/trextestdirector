"""TRex Test Director."""
import argparse
import logging
import os

from trextestdirector.trex_stl_scenario import TrexStlScenario
from trextestdirector.utilities import load_config, set_up_logging, save_results_to_file

logger = logging.getLogger(__name__)


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="trextestdirector",
        description="A tool for creating and running test scenarios for TRex",
    )
    parser.add_argument("config", help="path to a yaml config file")
    parser.add_argument(
        "-s", "--scenario", help="path to a test scenario to run", default=None
    )
    parser.add_argument(
        "-l", "--log_config", help="path to a yaml file with logging configuration"
    )
    parser.add_argument(
        "-o", "--output_file", help="path to file where statistics will be saved"
    )
    args = parser.parse_args()
    if not args.scenario:
        args.scenario = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "default_scenario.py"
        )
    return args


if __name__ == "__main__":
    args = parse_args()
    set_up_logging(args.log_config)
    config = load_config(args.config)
    TrexTest = TrexStlScenario.load_trex_test_scenario(args.scenario)
    test = TrexTest(config)
    test.run()
    if args.output_file:
        save_results_to_file(test.statistics, args.output_file)
