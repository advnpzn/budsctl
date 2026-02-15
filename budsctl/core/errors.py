"""Domain-specific errors for budsctl."""


class BudsctlError(Exception):
    """Base error for budsctl."""


class PluginValidationError(BudsctlError):
    """Raised when a plugin file does not conform to schema or semantics."""


class PluginLoadError(BudsctlError):
    """Raised when loading plugin sources fails."""


class DeviceSelectionError(BudsctlError):
    """Raised when device matching cannot resolve a single target."""


class DeviceDiscoveryError(BudsctlError):
    """Raised when Bluetooth device discovery command(s) fail."""


class FeatureResolutionError(BudsctlError):
    """Raised when feature/value cannot be found for a plugin."""


class TransportError(BudsctlError):
    """Base transport error."""


class TransportConnectError(TransportError):
    """Raised on RFCOMM connect failures."""


class TransportSendError(TransportError):
    """Raised when payload sending fails."""


class TransportTimeoutError(TransportError):
    """Raised when RFCOMM receive times out."""
