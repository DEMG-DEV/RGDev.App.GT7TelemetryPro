import sys
import os
import logging

# Cambiar el directorio de trabajo al directorio de datos estándar del sistema
# para que los logs, configuraciones y BD se guarden de manera segura.
def get_app_data_dir():
    app_name = "GT7TelemetryPro"
    if sys.platform == 'win32':
        return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), app_name)
    elif sys.platform == 'darwin':
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    else:
        return os.path.join(os.path.expanduser('~'), '.local', 'share', app_name)

app_data_dir = get_app_data_dir()
os.makedirs(app_data_dir, exist_ok=True)
os.chdir(app_data_dir)

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
    app.setStyle("Fusion")
    
    # Forzar paleta diurna (Light Mode) para ignorar el Dark Mode del SO
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = TelemetryMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
