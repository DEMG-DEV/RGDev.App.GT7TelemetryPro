from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer

class AlertWidget(QWidget):
    """
    Panel de notificaciones del Pit-Wall.
    Muestra alertas visuales y emite pitidos en casos críticos.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.title_label = QLabel("Pit-Wall Alerts")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.title_label)
        
        self.alert_labels = []
        
        # Estilos por severidad
        self.styles = {
            "INFO": "background-color: #2E86C1; color: white; padding: 10px; border-radius: 5px; font-weight: bold;",
            "WARNING": "background-color: #F39C12; color: black; padding: 10px; border-radius: 5px; font-weight: bold;",
            "CRITICAL": "background-color: #C0392B; color: white; padding: 10px; border-radius: 5px; font-weight: bold; border: 2px solid yellow;"
        }
        
    def push_alert(self, severity: str, title: str, message: str):
        """
        Agrega una nueva alerta a la pila.
        """
        label = QLabel(f"{title}: {message}")
        label.setStyleSheet(self.styles.get(severity, self.styles["INFO"]))
        label.setWordWrap(True)
        self.layout.addWidget(label)
        self.alert_labels.append(label)
        
        # Sonido para alertas críticas o warnings
        if severity in ["CRITICAL", "WARNING"]:
            QApplication.beep()
            
        # Eliminar la alerta después de X segundos
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._remove_alert(label))
        
        duration = 10000 if severity == "CRITICAL" else 5000
        timer.start(duration)
        
        # Mantener solo las últimas 3 alertas para no desbordar la pantalla
        while len(self.alert_labels) > 3:
            oldest = self.alert_labels[0]
            self._remove_alert(oldest)
            
    def _remove_alert(self, label: QLabel):
        if label in self.alert_labels:
            self.alert_labels.remove(label)
            try:
                label.deleteLater()
            except RuntimeError:
                pass
