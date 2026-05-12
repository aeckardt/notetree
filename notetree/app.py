#!/usr/bin/env python3

import sys
import os
import pathlib

from PyQt6.QtCore import (QLocale, QTranslator)
from PyQt6.QtWidgets import (QApplication)

from notetree.common.utils.settings import settings
from notetree.common.utils.workingdirectory import working_directory
from notetree.library.base.indexcounter import indexcounter
from notetree.library.icons.datacontainer import icons
from notetree.mainwindow import MainWindow as MainWindow

def install_translator(app, language: str | None = None) -> bool:
    """
    Installs an application translator.

    language:
        "de" -> loads notetree_de.qm
        "en" -> no translator, because English is currently the source language
        None -> uses system language
    """
    global _translator

    if language is None:
        language = QLocale.system().name().split("_")[0]

    if language == "en":
        return False

    translations_dir = "translations"
    qm_file = f"notetree_{language}.qm"

    translator = QTranslator(app)

    if translator.load(qm_file, str(translations_dir)):
        app.installTranslator(translator)
        _translator = translator  # keep alive
        return True

    return False

def main(argv):
    org_name = "aeckardt"
    app_name = "notetree"

    if sys.platform.startswith('darwin'):
        try:
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                app_info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if app_info:
                    app_info['CFBundleName'] = app_name
        except ImportError:
            pass

    indexcounter.load()
    icons.load()
    settings.load()

    app = QApplication(argv)

    app.setApplicationName(app_name)
    app.setOrganizationName(org_name)

    # Translate strings according to system standard
    # Available languages are currently
    # - English (en_US)
    # - German (de_DE)
    lang = settings.get("language")
    install_translator(app, lang)

    # Suppress specific Qt warnings
    os.environ["QT_LOGGING_RULES"] = "*.debug=false"

    window = MainWindow()
    window.setup_ui()
    window.show()

    result = app.exec()

    indexcounter.save()
    icons.save()
    settings.save()

    return result

if __name__ == '__main__':
    with working_directory(pathlib.Path(__file__).parent.parent.resolve()):
        sys.exit(main(sys.argv))
