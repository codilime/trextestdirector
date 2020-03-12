import logging

from trextestdirector import TrexStlProfile

from trex_stl_lib.api import (
    IP,
    UDP,
    Ether,
    STLFlowLatencyStats,
    STLFlowStats,
    STLPktBuilder,
    STLStream,
    STLTXCont,
)

logger = logging.getLogger(__name__)


class LatencyProfile(TrexStlProfile):
    def __init__(self):
        self.tunables = {
            "pkt_data": "X",
            "pkt_size": 64,
            "pps": 1000,
            "src_ip": "192.168.0.1",
            "dst_ip": "192.168.0.2",
            "flow_stats": "latency",
            "flow_stats_pps": 10,
            "flow_stats_pg_id": 0,
        }

    def create_streams(self):
        base_pkt = (
            Ether()
            / IP(src=self.tunables["src_ip"], dst=self.tunables["dst_ip"])
            / UDP(chksum=0)
        )
        pkt_size = self.tunables["pkt_size"] - 4  # HW will add 4 bytes ethernet FCS
        pad = self.tunables["pkt_data"] * max(0, pkt_size - len(base_pkt))
        if len(pad) < 16:
            raise Exception(
                "At least 16 bytes payload is needed for latency measurements"
            )
        pkt = base_pkt / pad
        stream = STLStream(
            packet=STLPktBuilder(pkt=pkt), mode=STLTXCont(pps=self.tunables["pps"])
        )
        streams = [stream]
        flow_stats = self.tunables["flow_stats"]
        if flow_stats == "stats":
            latency_stream = STLStream(
                packet=STLPktBuilder(pkt=pkt),
                mode=STLTXCont(pps=self.tunables["flow_stats_pps"]),
                flow_stats=STLFlowStats(pg_id=self.tunables["flow_stats_pg_id"]),
            )
        elif flow_stats == "latency":
            latency_stream = STLStream(
                packet=STLPktBuilder(pkt=pkt),
                mode=STLTXCont(pps=self.tunables["flow_stats_pps"]),
                flow_stats=STLFlowLatencyStats(pg_id=self.tunables["flow_stats_pg_id"]),
            )
            streams.append(latency_stream)
        elif not flow_stats:
            pass
        else:
            error_msg = (
                f"Unknown flow stats type {flow_stats}. Available types: stats, latency"
            )
            raise Exception(error_msg)
        return streams


# dynamic load - used for trex console or simulator
def register():
    return LatencyProfile()
