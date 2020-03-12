from trextestdirector.trex_stl_scenario import TrexStlScenario


class DefaultScenario(TrexStlScenario):
    """Default TRex stateless mode test scenario."""

    def __init__(self, config):
        super().__init__(config)

    def test(self):
        """Scenario test."""
        self.start_traffic()
