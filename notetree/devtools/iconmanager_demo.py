#!/usr/bin/env python3

from PyQt6.QtWidgets import (QApplication)

import pathlib
import sys

from notetree.common.utils.settings import settings
from notetree.common.utils.workingdirectory import working_directory
from notetree.library.base.indexcounter import indexcounter
from notetree.library.icons.datacontainer import icons
from notetree.library.icons.managerdialog import IconManagerDialog

def main(argv):
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

    sys.exit(result)

if __name__ == '__main__':
    with working_directory(pathlib.Path(__file__).parent.parent.parent.resolve()):
        sys.exit(main(sys.argv))
