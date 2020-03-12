import sys
import time
from abc import ABC
from collections import OrderedDict

from trextestdirector.utilities import format_num

from trex.common.stats.trex_global_stats import GlobalStats
from trex.common.stats.trex_port_stats import PortStats
from trex.utils import text_tables


class TrexStats(text_tables.Tableable):
    def __init__(self, stats):
        self.stats = stats

    def _get(self, src, field, default=None):
        if isinstance(field, list):
            value = src
            for level in field:
                if level not in value:
                    return default
                value = value[level]
        else:
            if field not in src:
                return default
            value = src[field]

        return value

    def get(self, field, format=False, unit="", compact=True):
        value = self._get(self.stats, field)
        if value == None:
            return "N/A"
        if format:
            value = format_num(value, unit, compact)
        return value

    def to_dict(self):
        raise NotImplementedError()


class TrexPortStats(TrexStats):
    def __init__(self, stats, port_id=""):
        super().__init__(stats)
        self.port_id = port_id

    def to_table(self):
        stats = OrderedDict(
            [
                ("TX pkts", self.get("opackets", True)),
                ("RX pkts", self.get("ipackets", True)),
                ("---", ""),
                ("TX bytes", self.get("obytes", True)),
                ("RX bytes", self.get("ibytes", True)),
                ("----", ""),
                ("TX errors", self.get("oerrors")),
                ("RX errors", self.get("ierrors")),
            ]
        )

        total_cols = 1
        stats_table = text_tables.TRexTextTable("Port statistics")
        stats_table.set_cols_align(["l"] + ["r"] * total_cols)
        stats_table.set_cols_width([10] + [17] * total_cols)
        stats_table.set_cols_dtype(["t"] + ["t"] * total_cols)

        stats_table.add_rows([[k] + [v] for k, v in stats.items()], header=False)

        stats_table.header(["port", self.port_id])

        return stats_table


class TrexPortStatsSum(TrexPortStats):
    def __init__(self, stats):
        super().__init__(stats, port_id="")

    @staticmethod
    def __merge_dicts(target, src):
        for k, v in src.items():
            if k in target:
                target[k] += v
            else:
                target[k] = v

    def __radd__(self, other):
        if (other == None) or (other == 0):
            return self
        else:
            return self.__add__(other)

    def __add__(self, other):
        assert isinstance(other, TrexPortStats)

        # main stats
        if not self.stats:
            self.stats = {}

        self.__merge_dicts(self.stats, other.stats)

        return self


class TrexLatencyStats(TrexStats):
    def __init__(self, stats):
        super().__init__(stats)

    def to_table(self):
        pg_ids = [pg_id for pg_id in self.stats["latency"] if isinstance(pg_id, int)]
        if not pg_ids:
            return text_tables.TRexTextTable("")
        stream_count = len(pg_ids)
        stats_table = text_tables.TRexTextTable("Latency statistics")
        stats_table.set_cols_align(["l"] + ["r"] * stream_count)
        stats_table.set_cols_width([13] + [14] * stream_count)
        stats_table.set_cols_dtype(["t"] + ["t"] * stream_count)
        header = ["PG ID"] + [key for key in pg_ids]
        stats_table.header(header)
        stats_data = OrderedDict([("TX pkts", []), ("RX pkts", []),])
        for pg_id in pg_ids:
            stats_data["TX pkts"].append(
                self.get(["flow_stats", pg_id, "tx_pkts", "total"], format=True)
            )
            stats_data["RX pkts"].append(
                self.get(["flow_stats", pg_id, "rx_pkts", "total"], format=True)
            )
        # Check if server is receiving latency packets. If so, then it has full
        # latency informations. Otherwise it knows only how many latency packets
        # were sent.
        # stats_data contains formatted text so data could be like "XXX K" so
        # we need to split value and suffix.
        if any(float(rx_pkts.split()[0]) > 0.0 for rx_pkts in stats_data["RX pkts"]):
            stats_data.update(
                OrderedDict(
                    [
                        ("---", [""] * stream_count),
                        ("Jitter", []),
                        ("Errors", []),
                        ("----", [""] * stream_count),
                        ("Max latency", []),
                        ("Min latency", []),
                        ("Avg latency", []),
                    ]
                )
            )
            for pg_id in pg_ids:
                stats_data["Avg latency"].append(
                    self.get(
                        ["latency", pg_id, "latency", "average"], True, "us", False
                    )
                )
                stats_data["Max latency"].append(
                    self.get(
                        ["latency", pg_id, "latency", "total_max"], True, "us", False
                    )
                )
                stats_data["Min latency"].append(
                    self.get(
                        ["latency", pg_id, "latency", "total_min"], True, "us", False
                    )
                )
                stats_data["Jitter"].append(
                    self.get(["latency", pg_id, "latency", "jitter"], True)
                )
                errors = 0
                seq_too_low = self.get(["latency", pg_id, "err_cntrs", "seq_too_low"])
                errors += seq_too_low
                seq_too_high = self.get(["latency", pg_id, "err_cntrs", "seq_too_high"])
                errors += seq_too_high
                stats_data["Errors"].append(errors)
            stats_table.add_rows([[k] + v for k, v in stats_data.items()], header=False)
            merged_histogram = {}
            for pg_id in pg_ids:
                merged_histogram.update(
                    self.stats["latency"][pg_id]["latency"]["histogram"]
                )
            max_histogram_size = 17
            histogram_size = min(max_histogram_size, len(merged_histogram))
            stats_table.add_row(["-----"] + [" "] * stream_count)
            stats_table.add_row(["- Histogram -"] + [" "] * stream_count)
            stats_table.add_row(["    [us]     "] + [" "] * stream_count)
            for i in range(max_histogram_size - histogram_size):
                if i == 0 and not merged_histogram:
                    stats_table.add_row(["   No Data   "] + [" "] * stream_count)
                else:
                    stats_table.add_row([" "] * (stream_count + 1))
            for key in list(reversed(sorted(merged_histogram.keys())))[:histogram_size]:
                hist_vals = []
                for pg_id in pg_ids:
                    hist_vals.append(
                        self.stats["latency"][pg_id]["latency"]["histogram"].get(
                            key, " "
                        )
                    )
                stats_table.add_row([key] + hist_vals)

            stats_table.add_row(["- Counters -"] + [" "] * stream_count)
            err_cntrs_dict = OrderedDict()
            for pg_id in pg_ids:
                for err_cntr in sorted(
                    self.stats["latency"][pg_id]["err_cntrs"].keys()
                ):
                    if err_cntr not in err_cntrs_dict:
                        err_cntrs_dict[err_cntr] = [
                            self.stats["latency"][pg_id]["err_cntrs"][err_cntr]
                        ]
                    else:
                        err_cntrs_dict[err_cntr].append(
                            self.stats["latency"][pg_id]["err_cntrs"][err_cntr]
                        )
            for err_cntr, val_list in err_cntrs_dict.items():
                stats_table.add_row([err_cntr] + val_list)
        else:
            stats_table.add_rows([[k] + v for k, v in stats_data.items()], header=False)
        return stats_table


def print_port_stats(server, buffer=sys.stdout):
    client = server["client"]
    port_ids = [port["id"] for port in server["ports"]]
    stats = client.get_stats(port_ids)

    tables = [TrexPortStats(stats[port_id], port_id).to_table() for port_id in port_ids]
    if len(port_ids) > 1:
        tables.append(TrexPortStats(stats["total"], "total").to_table())
    table = text_tables.TRexTextTable.merge(tables)
    text_tables.print_table_with_header(table, table.title, buffer=buffer)


def print_latency_stats(server, buffer=sys.stdout):
    client = server["client"]
    port_ids = [port["id"] for port in server["ports"]]
    stats = TrexLatencyStats(client.get_stats(port_ids))
    table = stats.to_table()
    text_tables.print_table_with_header(table, table.title, buffer=buffer)
