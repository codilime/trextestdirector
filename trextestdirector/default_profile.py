import logging

from trextestdirector.trex_stl_profile import TrexStlProfile

from trex_stl_lib.api import (
    IP,
    UDP,
    Ether,
    STLPktBuilder,
    STLStream,
    STLTXCont,
)

logger = logging.getLogger(__name__)


class DefaultProfile(TrexStlProfile):
    """Default TRex traffic profile."""

    def __init__(self):
        self.tunables = {
            "pkt_data": "X",
            "pkt_size": 64,
            "pps": 1000,
            "src_ip": "192.168.0.1",
            "dst_ip": "192.168.0.2",
        }

    def create_streams(self):
        base_pkt = Ether() / IP(
            src=self.tunables["src_ip"], dst=self.tunables["dst_ip"]
        ) / UDP(chksum=0)
        pkt_size = self.tunables["pkt_size"] - 4  # HW will add 4 bytes ethernet FCS
        pad = self.tunables["pkt_data"] * max(0, pkt_size - len(base_pkt))
        pkt = base_pkt / pad
        return STLStream(
            packet=STLPktBuilder(pkt=pkt), mode=STLTXCont(pps=self.tunables["pps"])
        )


def register():
    """Register profile."""
    return DefaultProfile()
