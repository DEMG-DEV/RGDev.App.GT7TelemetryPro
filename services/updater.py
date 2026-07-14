import os
import sys
import json
import urllib.request
import zipfile
import subprocess
import shutil
import time
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import APP_VERSION, GITHUB_REPO

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str) # version, download_url
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'GT7TelemetryPro-Updater'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get('tag_name', '').lstrip('v')
                if not latest_version:
                    return
                
                # Very basic version comparison (assumes format x.y.z)
                if self.is_newer(APP_VERSION, latest_version):
                    # Find appropriate asset
                    download_url = None
                    os_keyword = "macOS" if sys.platform == "darwin" else "Windows"
                    
                    for asset in data.get('assets', []):
                        if os_keyword.lower() in asset['name'].lower() and asset['name'].endswith('.zip'):
                            download_url = asset['browser_download_url']
                            break
                    
                    if download_url:
                        self.update_available.emit(latest_version, download_url)
                        
        except Exception as e:
            self.error_occurred.emit(f"Error checking for updates: {str(e)}")

    def is_newer(self, current_ver, latest_ver):
        # Convert versions like "1.0.0" to tuples (1, 0, 0)
        try:
            cur_parts = tuple(map(int, current_ver.split('.')))
            lat_parts = tuple(map(int, latest_ver.split('.')))
            return lat_parts > cur_parts
        except:
            return False

class UpdateDownloader(QThread):
    progress_update = pyqtSignal(int)
    download_complete = pyqtSignal(str) # Path to the extracted update
    error_occurred = pyqtSignal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            # Create a temporary directory in AppData for downloading
            app_name = "GT7TelemetryPro"
            if sys.platform == 'win32':
                temp_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), app_name, 'updates')
            elif sys.platform == 'darwin':
                temp_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name, 'updates')
            else:
                temp_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', app_name, 'updates')
                
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download file
            zip_path = os.path.join(temp_dir, 'update.zip')
            
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'GT7TelemetryPro-Updater'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                bytes_so_far = 0
                
                with open(zip_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_so_far += len(chunk)
                        if total_size > 0:
                            percent = int(bytes_so_far * 100 / total_size)
                            self.progress_update.emit(percent)
                            
            # Extract zip
            extract_dir = os.path.join(temp_dir, 'extracted')
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                if sys.platform == 'darwin':
                    # Python's zipfile destroys symlinks, which corrupts macOS .app bundles (Qt frameworks).
                    # Use native macOS unzip command to preserve symlinks and permissions.
                    import subprocess
                    subprocess.run(['unzip', '-q', '-o', zip_path, '-d', extract_dir], check=True)
                else:
                    for info in zip_ref.infolist():
                        extracted_path = zip_ref.extract(info, extract_dir)
                        if info.external_attr > 0:
                            try:
                                # Restaura los permisos originales del archivo
                                os.chmod(extracted_path, info.external_attr >> 16)
                            except Exception:
                                pass
                
            self.download_complete.emit(extract_dir)
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to download/extract update: {str(e)}")


def apply_update_and_restart(extracted_dir):
    """
    Creates and executes a relay script that waits for the main app to close,
    overwrites the application files, and restarts the app.
    """
    try:
        if sys.platform == 'darwin':
            # macOS .app bundle replacement
            # sys.executable is usually Contents/MacOS/GT7TelemetryPro
            # We need to replace the entire .app directory.
            # However, if running from Python directly (not bundled), sys.executable is python.
            if "GT7TelemetryPro.app" in sys.executable:
                current_app_path = sys.executable
                while not current_app_path.endswith('.app'):
                    current_app_path = os.path.dirname(current_app_path)
            else:
                # Fallback for development: just copy over the cwd
                current_app_path = os.getcwd()

            # Find the new .app inside extracted_dir (might be nested)
            new_app_path = None
            for root, dirs, files in os.walk(extracted_dir):
                for d in dirs:
                    if d.endswith('.app'):
                        new_app_path = os.path.join(root, d)
                        break
                if new_app_path:
                    break
            
            if not new_app_path:
                print("No .app found in the update zip.")
                return

            script_path = os.path.join(extracted_dir, "updater.sh")
            with open(script_path, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("sleep 2\n") # Wait for app to close
                f.write(f"rm -rf \"{current_app_path}\"\n")
                f.write(f"mv \"{new_app_path}\" \"{current_app_path}\"\n")
                f.write(f"xattr -cr \"{current_app_path}\" || true\n") # Eliminar modo cuarentena
                f.write(f"chmod +x \"{current_app_path}/Contents/MacOS/\"* || true\n") # Asegurar permisos de ejecución
                f.write(f"open \"{current_app_path}\"\n")
                
            os.chmod(script_path, 0o755)
            subprocess.Popen([script_path], start_new_session=True)
            
        elif sys.platform == 'win32':
            # Windows executable replacement
            if sys.executable.endswith("GT7TelemetryPro.exe"):
                current_app_dir = os.path.dirname(sys.executable)
                exe_name = os.path.basename(sys.executable)
            else:
                current_app_dir = os.getcwd()
                exe_name = "GT7TelemetryPro.exe"
                
            script_path = os.path.join(extracted_dir, "updater.bat")
            with open(script_path, "w") as f:
                f.write("@echo off\n")
                f.write("timeout /t 2 /nobreak >nul\n") # Wait for app to close
                f.write(f"xcopy /s /e /y \"{extracted_dir}\\*\" \"{current_app_dir}\\\"\n")
                f.write(f"start \"\" \"{os.path.join(current_app_dir, exe_name)}\"\n")
                
            subprocess.Popen([script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
        sys.exit(0)
    except Exception as e:
        print(f"Failed to apply update: {e}")
