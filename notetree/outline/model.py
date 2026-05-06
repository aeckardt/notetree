from PyQt6.QtCore import (QAbstractItemModel, QObject, QModelIndex, Qt, pyqtSignal)
from PyQt6.QtGui import (QTextDocument)

class OutlineItem:
    def __init__(self, description : str = '', block_index: int = -1, parent = None):
        self._children = []
        self._description = description
        self._block_index = block_index
        self._parent = parent

    def append_child(self, child):
        self._children.append(child)

    def block_index(self):
        return self._block_index

    def child(self, row):
        return self._children[row]

    def child_count(self):
        return len(self._children)

    def description(self):
        return self._description

    def parent(self):
        return self._parent

    def remove_child(self, row):
        self._children.pop(row)

    def row(self):
        if self._parent is None:
            return 0

        for row in range(len(self._parent._children)):
            child = self._parent._children[row]
            if self == child:
                return row
        
        return -1

    def set_block_index(self, blockIndex):
        self._block_index = blockIndex

    def set_description(self, description):
        self._description = description

    def swap(self, ix1, ix2):
        self._children[ix1], self._children[ix2] = self._children[ix2], self._children[ix1]

class OutlineModel(QAbstractItemModel):
    loaded = pyqtSignal()

    def __init__(self, parent : QObject = None):
        QAbstractItemModel.__init__(self, parent)

        self._root_item = None

    def append_item(self, description: str, type: int, parent: QModelIndex):
        if parent.isValid():
            parent_item = parent.internalPointer()
        elif self._root_item is not None:
            parent_item = self._root_item
        else:
            raise Exception('Cannot add items without a root item')

        row = parent_item.child_count()

        self.beginInsertRows(parent, row, row)
        node = OutlineItem(description, type, parent_item)
        parent_item.append_child(node)
        self.endInsertRows()

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return item.description()

        return None

    def flags(self, index):
        if index.isValid():
            return QAbstractItemModel.flags(self, index)
        else:
            return Qt.ItemFlag.NoItemFlags

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if parent.isValid():
            parent_item = parent.internalPointer()
        elif self._root_item is not None:
            parent_item = self._root_item
        else:
            return QModelIndex()
        child_item = parent_item.child(row)
        return self.createIndex(row, column, child_item)

    def iterate(self, index: QModelIndex, func, depth = 0):
        if index.isValid():
            func(index)

        if not self.hasChildren(index):
            return

        row_count = self.rowCount(index)
        column_count = self.columnCount(index)

        for row in range(row_count):
            for column in range(column_count):
                self.iterate(self.index(row, column, index), func, depth + 1)

    def iterate_all(self, func):
        root = self.root_index()
        return self.iterate(root, func)

    def load_document(self, document: QTextDocument):
        self.beginResetModel()
        self._setup_model_data(document)
        self.endResetModel()

        self.loaded.emit()

    def clear(self):
        self.beginResetModel()
        self._root_item = OutlineItem()
        self.endResetModel()

        self.loaded.emit()

    def moveRow(self, source_parent, source_row, destination_parent, destination_child):
        if source_parent != destination_parent:
            return False

        parent_item = source_parent.internalPointer()
        parent_item.swap(source_row, destination_child)

        return True

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item == None:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def remove_item(self, index: QModelIndex):
        if index.isValid():
            item = index.internalPointer()
        else:
            raise Exception('Invalid item cannot be removed')

        if index.parent().isValid():
            parent_index = index.parent()
            parent_item = parent_index.internalPointer()
        elif self._root_item is not None:
            parent_index = QModelIndex()
            parent_item = self._root_item
        else:
            raise Exception('Cannot remove item without a root item')

        row = item.row()

        self.beginRemoveRows(parent_index, row, row)
        parent_item.remove_child(row)
        self.endRemoveRows()

    def root_index(self):
        return QModelIndex()

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if parent.isValid():
            parent_item = parent.internalPointer()
        elif self._root_item is not None:
            parent_item = self._root_item
        else:
            return 0

        return parent_item.child_count()

    def update_index(self, index: QModelIndex):
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

    def _setup_model_data(self, document: QTextDocument):
        self._root_item = OutlineItem()
        heading_stack = []
        caption = ''

        block_count = document.blockCount()
        for n in range(block_count):
            block = document.findBlockByNumber(n)
            block_fmt = block.blockFormat()

            heading_lvl = block_fmt.headingLevel()
            if heading_lvl <= 0:
                continue

            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                caption += fragment.text()

                it += 1

            item_added = False
            while not item_added and len(heading_stack) > 0:
                last_heading_lvl, last_heading_item = heading_stack[-1]
                if heading_lvl > last_heading_lvl:
                    child_item = OutlineItem(caption, n, last_heading_item)
                    last_heading_item.append_child(child_item)
                    heading_stack.append([heading_lvl, child_item])
                    item_added = True
                else:
                    heading_stack.pop()

            if not item_added:
                child_item = OutlineItem(caption, n, self._root_item)
                self._root_item.append_child(child_item)
                heading_stack.append([heading_lvl, child_item])
            
            caption = ''
