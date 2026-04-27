import os

from PyQt6.QtCore import (QSize, QRect, QModelIndex)
from PyQt6.QtGui import (QImage)
from PyQt6.QtWidgets import (QWidget, QItemDelegate, QTreeView)

from notetree.documenttree.treemodel import ITEM_ICON_ROLE
from notetree.library.icons.datacontainer import icons

ITEM_SIZE = 16

class DocumentTreeViewDelegate(QItemDelegate):
    def __init__(self):
        QItemDelegate.__init__(self)

    def sizeHint(self, option, index):
        return QSize(ITEM_SIZE + 6, ITEM_SIZE + 6)

class DocumentTreeView(QTreeView):
    def __init__(self, parent : QWidget = None):
        super().__init__(parent)
        delegate = DocumentTreeViewDelegate()
        self.setItemDelegate(delegate)
        self.setIconSize(QSize(ITEM_SIZE, ITEM_SIZE))

    def drawBranches(self, painter, rect, index):
        icon_index = index.data(ITEM_ICON_ROLE)
        if icon_index is None:
            return

        std_size = ITEM_SIZE
        if index.parent() != QModelIndex():
            if rect.width() > std_size:
                offset = rect.width() - std_size
                rect.setX(rect.x() + offset)
                rect.setWidth(std_size)
        if rect.width() > rect.height():
            offset = rect.width() - rect.height()
            rect = QRect(rect.x() + int(offset / 2), rect.y(), rect.height(), rect.height())
        if rect.height() > rect.width():
            offset = rect.height() - rect.width()
            rect = QRect(rect.x(), rect.y() + int(offset / 2), rect.width(), rect.width())

        icon = icons.from_index(icon_index)
        filename = f'{os.getcwd()}/icons/{icon['path']}'
        img = QImage(filename, 'PNG')
        painter.drawImage(rect, img)
