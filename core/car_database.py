import json
import logging
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


class CarDatabase:
    """Singleton service to load and query GT7 car information."""
    _instance = None
    
    def __new__(cls, json_path='gt7_cars.json'):
        if cls._instance is None:
            cls._instance = super(CarDatabase, cls).__new__(cls)
            if not hasattr(cls._instance, 'car_db'):
                cls._instance._initialize(json_path)
        return cls._instance
        
    def _initialize(self, json_path):
        self.car_db = {}
        try:
            # Check if json_path is an absolute path or relative
            if not os.path.isabs(json_path):
                json_path = resource_path(json_path)
                
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.car_db = json.load(f)
                logging.info(f"Loaded {len(self.car_db)} cars from {json_path}")
            else:
                logging.warning(f"Car database {json_path} not found.")
        except Exception as e:
            logging.warning(f"Could not load {json_path}: {e}")
            
    def get_car_name(self, car_code: int) -> str:
        """Returns the full name of the car, or a generic ID string if not found."""
        car_info = self.car_db.get(str(car_code))
        if car_info:
            return car_info.get("full_name", f"Auto ID: {car_code}")
        return f"Auto ID: {car_code}"
