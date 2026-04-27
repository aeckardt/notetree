import os

from PyQt6.QtCore import (Qt)
from PyQt6.QtGui import (QPixmap)

from notetree.library.base.column import ColumnFormat
from notetree.library.base.indexedtablemodel import IndexedTableModel
from notetree.library.icons.datacontainer import icons

class IconModel(IndexedTableModel):
    def __init__(self):
        super().__init__(icons)

        self.add_column('Name',      'name',   ColumnFormat.String)
        self.add_column('Design',    'design', ColumnFormat.String)
        self.add_column('Dateiname', 'path',   ColumnFormat.String)

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.TextAlignmentRole:
            key = self.key(index.column())
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        elif role != Qt.ItemDataRole.DisplayRole and role != Qt.ItemDataRole.DecorationRole:
            return None

        key = self.key(index.column())
        icon = self.item_at(index.row())

        if role == Qt.ItemDataRole.DisplayRole:
            if key != 'design':
                return icon.get(key, '')
            else:
                if 'design' in icon:
                    design_type = icon['design']
                    match design_type:
                        case 0:
                            return 'Standard'
                        case 1:
                            return 'Flat'
        elif key == 'name' and role == Qt.ItemDataRole.DecorationRole:
            if 'path' in icon:
                filename = f'{os.getcwd()}/icons/{icon['path']}'
                if os.path.exists(filename):
                    pixmap = QPixmap(filename, 'PNG')
                    if pixmap.height() == 24:
                        pixmap = pixmap.scaledToHeight(16)
                    elif pixmap.height() > 18:
                        pixmap = pixmap.scaledToHeight(18)
                    return pixmap

        return None
