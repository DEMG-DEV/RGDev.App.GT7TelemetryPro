import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import TelemetryMainWindow

logging.basicConfig(
    filename='gt7_telemetry.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    filemode='a'
)

import signal

def main():
    # Habilitar Ctrl+C (SIGINT) nativo en PyQt6
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    window = TelemetryMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
