# Traffic profiles

TRex Test Director's traffic profile is a Python file created in accordance with TRex rules (see [TRex STL Python API](https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/profile_code.html) and [TRex tutorial](https://trex-tgn.cisco.com/trex/doc/trex_stateless.html#_tutorial_advanced_traffic_profile)) with following differences:

- profile class should inherits from Trex Test Director's `TrexStlProfile` class,
- profile class should implement `create_streams(self)` member function, which returns either one `STLStream` object or list of `STLStream` objects,
- profile tunables should be defined as key-value pairs in `tunables` member field (`self.tunables`),
- each profile will be loaded with `src_ip` and `dst_ip` tunables with values based on traffic direction defined in test. These values can be overriden in test config as `tunables`

## Example traffic profile file

```python
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


class ExampleProfile(TrexStlProfile):
    def __init__(self):
        self.tunables = {
            "pkt_data": "X",
            "pkt_size": 64,
            "pps": 1000,
            "src_ip": "192.168.0.1",
            "dst_ip": "192.168.0.2",
        }

    def create_streams(self):
        base_pkt = (
            Ether()
            / IP(src=self.tunables["src_ip"], dst=self.tunables["dst_ip"])
            / UDP(chksum=0)
        )
        pkt_size = self.tunables["pkt_size"] - 4  # HW will add 4 bytes ethernet FCS
        pad = self.tunables["pkt_data"] * max(0, pkt_size - len(base_pkt))
        pkt = base_pkt / pad
        stream = STLStream(
            packet=STLPktBuilder(pkt=pkt), mode=STLTXCont(pps=self.tunables["pps"])
        )
        streams = [stream]
        return streams


def register():
    return LatencyProfile()

```
