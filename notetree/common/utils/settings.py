import os
import json

from PyQt6.QtWidgets import (QWidget)

SETTINGS_PATH = "data/settings.json"

class Settings:
    def __init__(self):
        self.__data = {}

    def config(self, key: str, default = {}) -> dict:
        if key not in self.__data:
            self.__data[key] = default
        return self.__data[key]

    def contains(self, key: str) -> bool:
        return key in self.__data

    def get(self, key: str):
        return self.__data.get(key)

    def load(self):
        if os.path.isfile(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                self.__data = json.load(f)
        else:
            self.__data = {}

    def remove(self, key: str):
        if key in self.__data:
            del self.__data[key]

    def restore_geometry(self, window: QWidget):
        classname = window.__class__.__name__
        wnd_config = self.config(classname)

        vars = ['x', 'y', 'width', 'height']
        for var in vars:
            if var not in wnd_config or not type(wnd_config[var]) is int:
                # Validation failed
                # Geometry cannot be restored
                self.remove(classname)
                return
        x = wnd_config['x']
        y = wnd_config['y']
        w = wnd_config['width']
        h = wnd_config['height']
        window.setGeometry(x, y, w, h)

    def save(self):
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(self.__data, f, indent = 4, sort_keys = True,
                      separators=(',', ': '), ensure_ascii = False)

    def save_geometry(self, window: QWidget):
        wnd_config = self.window_config(window)
        wnd_config['x'] = window.geometry().x()
        wnd_config['y'] = window.geometry().y()
        wnd_config['width'] = window.geometry().width()
        wnd_config['height'] = window.geometry().height()

    def window_config(self, window: QWidget, default = {}):
        return self.config(window.__class__.__name__, default)


# Use Settings instance as Singleton
settings = Settings()
