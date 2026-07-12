from PyQt6.QtCore import QObject, pyqtSignal
from core.models import GT7TelemetryPacket

class TelemetryProvider(QObject):
    """
    Base class for telemetry providers (Live Network or Replay File).
    Emits a common packet_signal when new telemetry is available.
    """
    packet_signal = pyqtSignal(GT7TelemetryPacket)
    
    def start(self):
        """Starts providing telemetry data."""
        pass
        
    def stop(self):
        """Stops providing telemetry data."""
        pass
