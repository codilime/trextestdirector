class TrexTestDirectorError(Exception):
    """General TRex Test Director error."""

    pass


class TrexTestDirectorConfigError(TrexTestDirectorError):
    """TRex Test Director configuration file error."""

    pass


class TrexTestDirectorInterruptError(TrexTestDirectorError):
    pass
