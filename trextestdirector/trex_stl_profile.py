"""Traffic profile for TRex stateless client."""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TrexStlProfile(ABC):
    """Base class for TRex STL traffic profiles."""

    def __init__(self):
        self.tunables = {"src_ip": None, "dst_ip": None}

    @abstractmethod
    def create_streams(self, tunables):
        """Should implement streams."""

    def get_streams(self, **kwargs):
        """Return a list of streams."""
        for tunable, value in kwargs.items():
            if tunable in self.tunables:
                self.tunables[tunable] = value
            # TRex automatically injects 'direction' and 'port_id' while loading profile
            elif tunable not in ("direction", "port_id"):
                logger.warning(
                    f"tunable {tunable} is not applicable for profile {self.__class__.__name__}"
                )
        logger.debug(
            f"profile {self.__class__.__name__} loaded with tunables: {self.tunables}"
        )
        return self.create_streams()


# dynamic load - used for trex console or simulator
def register():
    """Register profile."""
    return TrexStlProfile()
