#!/usr/bin/env python3

from PyQt6.QtWidgets import (QApplication)

import pathlib
import sys

from notetree.common.utils.settings import settings
from notetree.common.utils.workingdirectory import working_directory
from notetree.library.base.indexcounter import indexcounter
from notetree.library.icons.datacontainer import icons
from notetree.library.icons.managerdialog import IconManagerDialog

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()

def main(argv):
    with working_directory(PROJECT_ROOT):
        indexcounter.load()
        icons.load()
        settings.load()

        app = QApplication(sys.argv)
        imd = IconManagerDialog()
        imd.show()
        result = app.exec()

        indexcounter.save()
        icons.save()
        settings.save()

    return result

if __name__ == '__main__':
    sys.exit(main(sys.argv))
