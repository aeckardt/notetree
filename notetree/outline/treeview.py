from PyQt6.QtCore import (QSize)
from PyQt6.QtWidgets import (QWidget, QItemDelegate, QTreeView)

ITEM_SIZE = 18

class OutlineDelegate(QItemDelegate):
    def __init__(self):
        QItemDelegate.__init__(self)

    def sizeHint(self, option, index):
        return QSize(ITEM_SIZE + 6, ITEM_SIZE + 6)

class OutlineTreeView(QTreeView):
    def __init__(self, parent : QWidget = None):
        super().__init__(parent)
        delegate = OutlineDelegate()
        self.setItemDelegate(delegate)
        self.setIconSize(QSize(ITEM_SIZE, ITEM_SIZE))

