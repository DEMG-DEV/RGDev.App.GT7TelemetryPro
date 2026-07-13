import sys
import os
import logging

# Cambiar el directorio de trabajo a Documentos para que los logs y BD se guarden ahí
# en lugar de intentar escribirse dentro de la aplicación o en la raíz (/)
app_doc_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'GT7TelemetryPro')
os.makedirs(app_doc_dir, exist_ok=True)
os.chdir(app_doc_dir)

from PyQt6.QtWidgets import QApplication
from ui.main_window import TelemetryMainWindow

logging.basicConfig(
    filename='gt7_telemetry.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    filemode='a'
)

import signal
import traceback

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Atrapa todas las excepciones no manejadas de la aplicación,
    incluyendo las generadas por PyQt6 que normalmente fallan silenciosamente.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Excepción Global No Capturada:", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    # Instalar hook global para errores
    sys.excepthook = global_exception_handler
    
    # Habilitar Ctrl+C (SIGINT) nativo en PyQt6
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    window = TelemetryMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
