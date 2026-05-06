from dataclasses import dataclass, field

from PyQt6.QtCore import (QModelIndex, QAbstractItemModel, QObject, pyqtSignal, Qt, QByteArray,
                          QDataStream, QIODevice, QMimeData)

from notetree.project.file import ProjectFile

@dataclass
class DocumentMetadata:
    """
    Represents metadata for one document in the project.
    That includes in particular its links (parent, children) to other documents.
    """

    # The unique ID is used to identify the document
    id: int | None = None

    # Name and icon of the document are visible in the treeview
    name: str = ''
    icon: str | None = None

    # Since documents are organized hierarchically in a tree,
    # they are also nodes (potentially) with a parent and children.
    parent: "DocumentMetadata | None" = None
    children: list["DocumentMetadata"] = field(default_factory=list)

    # Expanded state of treeview node
    expanded: bool = True

    # Markdown string of document text
    notes: str = ''

    def is_ancestor_of(self, other: "DocumentMetadata") -> bool:
        cur = other
        while cur is not None:
            if cur is self:
                return True
            cur = cur.parent
        return False

    def row(self) -> int:
        if self.parent is None:
            return 0

        sibling_count = len(self.parent.children)
        for row in range(sibling_count):
            child = self.parent.children[row]
            if self == child:
                return row
        
        return -1

    def swap(self, ix1, ix2):
        self.children[ix1], self.children[ix2] = self.children[ix2], self.children[ix1]

ITEM_ICON_ROLE = Qt.ItemDataRole.UserRole + 1
MIME_TYPE = "application/x-document-id"

class DocumentTreeModel(QAbstractItemModel):
    loaded = pyqtSignal()
    inserted = pyqtSignal(DocumentMetadata)
    removed = pyqtSignal(DocumentMetadata)
    data_changed = pyqtSignal()

    # -----------------------------------------------
    # 1. Standard TreeModel handlers (add, remove, ...)
    # -----------------------------------------------

    def __init__(self, parent: QObject | None = None):
        QAbstractItemModel.__init__(self, parent)

        # Invisible root above top level nodes (= "roots")
        self.super_root = DocumentMetadata()

        # Next unused document ID
        self.next_id = 1

        # Mapping: Document ID to corresponding QModelIndex
        self.index_from_id = {}

    def append_item(self, item: DocumentMetadata, parent: QModelIndex):
        if parent.isValid():
            parent_item = parent.internalPointer()
        elif self.super_root is not None:
            parent_item = self.super_root
        else:
            raise Exception('Cannot add items without a root item')

        row = len(parent_item.children)

        self.beginInsertRows(parent, row, row)
        if item.id is None:
            item.id = self.generate_id()
        item.parent = parent_item
        parent_item.children.append(item)
        self.endInsertRows()

        self.data_changed.emit()
        self.inserted.emit(item)

    def columnCount(self, _):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None

        item: DocumentMetadata = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        elif role == ITEM_ICON_ROLE:
            return item.icon

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
        elif self.super_root is not None:
            parent_item = self.super_root
        else:
            return QModelIndex()
        child_item = parent_item.children[row]
        index = self.createIndex(row, column, child_item)
        self.index_from_id[child_item.id] = index
        return index

    def moveRow(self, source_parent, source_row, destination_parent, destination_child):
        if source_parent != destination_parent:
            return False

        parent_item: DocumentMetadata = source_parent.internalPointer()
        if parent_item is not None:
            parent_item.swap(source_row, destination_child)
        else:
            self.super_root.swap(source_row, destination_child)

        self.data_changed.emit()

        return True

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent

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
        elif self.super_root is not None:
            parent_index = QModelIndex()
            parent_item = self.super_root
        else:
            raise Exception('Cannot remove item without a root item')

        row = item.row()

        self.beginRemoveRows(parent_index, row, row)
        parent_item.children.pop(row)
        self.endRemoveRows()

        self.data_changed.emit()
        self.removed.emit(item)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if parent.isValid():
            parent_item = parent.internalPointer()
        elif self.super_root is not None:
            parent_item = self.super_root
        else:
            return 0

        return len(parent_item.children)

    def update_index(self, index: QModelIndex):
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, ITEM_ICON_ROLE])

    # -----------------------------------------------
    # 2. ID handlers
    # -----------------------------------------------

    def generate_id(self) -> int:
        new_id = self.next_id
        self.next_id += 1
        return new_id

    def next_id(self) -> int:
        return self.next_id

    def root_ids(self):
        if self.super_root is None:
            return []

        ids = []
        root_count = len(self.super_root.children)
        for row in range(root_count):
            child_id = self.super_root.children[row].id
            ids.append(child_id)

        return ids

    # -----------------------------------------------
    # 3. Import / Export data
    # -----------------------------------------------

    def import_data(self, project: ProjectFile):
        self.beginResetModel()

        # Reset tree structure with new root
        self.super_root = DocumentMetadata()
        self.next_id = project.next_id

        # Generate list of all document IDs (ordered by their index in "project.documents")
        document_ids = []
        for doc in project.documents:
            document_ids.append(doc['id'])

        def integrate_item(item_id: int, parent_item: DocumentMetadata):
            """
            Integrate tree items recursively.
            """
            # Get dataset with specified ID from list
            item_dict = project.documents[document_ids.index(item_id)]

            # Build node (= DocumentMetadata object) from this dataset
            item = DocumentMetadata(item_dict['id'], item_dict['description'], item_dict.get('icon'), parent_item)
            if 'expanded' in item_dict:
                item.expanded = item_dict['expanded']
            if 'notes' in item_dict:
                item.notes = '\n'.join(item_dict['notes'])

            # Add children (if available)
            if 'children' in item_dict:
                for child_id in item_dict['children']:
                    if not child_id in document_ids:
                        raise Exception('Document referenced by id not found.')
                    integrate_item(child_id, item)

            # Link node to parent
            parent_item.children.append(item)

        # Build tree
        # Start with top level "root" items (under super root) 
        for root_id in project.root_ids:
            if not root_id in document_ids:
                raise Exception('Root referenced by id not found.')
            integrate_item(root_id, self.super_root)

        self.endResetModel()

        self.loaded.emit()

    def export_data(self, project: ProjectFile):
        # Clear data before export
        project.documents = []
        project.root_ids = []
        project.next_id = self.next_id

        def add_dataset(parent_item: DocumentMetadata, row: int, parent_dict: dict = None):
            """
            Build flat list recursively from tree.
            """
            # Get item from children list
            item = parent_item.children[row]

            # Add item ID to parent dataset
            if parent_dict is None:
                # No (visible) parent, add ID to "roots"
                project.root_ids.append(item.id)
            else:
                if 'children' not in parent_dict:
                    parent_dict['children'] = []
                parent_dict['children'].append(item.id)

            # Build dataset (dict) from DocumentMetadata object
            item_dict = {'description': item.name, 'id': item.id}
            if not item.expanded:
                item_dict['expanded'] = item.expanded
            if item.icon is not None:
                item_dict['icon'] = item.icon
            if item.notes is not None and len(item.notes) > 0:
                item_dict['notes'] = item.notes.splitlines()

            # Add dataset to documents list
            project.documents.append(item_dict)

            # Add children (if available)
            child_count = len(item.children)
            for row in range(child_count):
                add_dataset(item, row, item_dict)

        # Add all documents, starting with roots
        root_count = len(self.super_root.children)
        for row in range(root_count):
            add_dataset(self.super_root, row)

        # Sort by document ID
        # -> This vastly improves diffs between revisions
        project.documents = sorted(project.documents, key=lambda ds: ds['id'])

    # -----------------------------------------------
    # 4. Drag & Drop actions / flags
    # -----------------------------------------------

    def flags(self, index):
        Flag = Qt.ItemFlag
        base = Flag.ItemIsEnabled | Flag.ItemIsSelectable
        if not index.isValid():
            return base | Flag.ItemIsDropEnabled
        return base | Flag.ItemIsDragEnabled | Flag.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return [MIME_TYPE]

    def mimeData(self, indexes):
        indexes = [ix for ix in indexes if ix.isValid() and ix.column() == 0]
        if not indexes:
            return None
        src: QModelIndex = indexes[0]
        item: DocumentMetadata = src.internalPointer()

        ba = QByteArray()
        stream = QDataStream(ba, QIODevice.OpenModeFlag.WriteOnly
                             if hasattr(QIODevice, "OpenModeFlag") else QIODevice.OpenModeFlag.WriteOnly)
        stream.writeInt32(item.id)

        md = QMimeData()
        md.setData(MIME_TYPE, ba)
        return md

    def dropMimeData(self, data, action, row, column, parent_index: QModelIndex):
        if action != Qt.DropAction.MoveAction:
            return False
        if not data or not data.hasFormat(MIME_TYPE):
            return False

        if parent_index.isValid():
            dst_parent = parent_index.internalPointer()
        else:
            dst_parent = self.super_root

        # The given row is where the item should be inserted
        # It is -1, when no row is specified

        if row == -1:
            dst_row = len(dst_parent.children)
        else:
            dst_row = row

        # Determine source
        ba = data.data(MIME_TYPE)
        stream = QDataStream(ba, QIODevice.OpenModeFlag.ReadOnly
                             if hasattr(QIODevice, "OpenModeFlag") else QIODevice.OpenModeFlag.ReadOnly)
        src_id = stream.readInt32()

        if src_id in self.index_from_id:
            src_index: QModelIndex = self.index_from_id[src_id]
        else:
            return False
        src_item: DocumentMetadata = src_index.internalPointer()
        src_parent: DocumentMetadata = src_item.parent
        if src_parent is None:
            return False

        # Don't drop into itself / own ancestors
        if src_item.is_ancestor_of(dst_parent):
            return False

        if src_parent.id in self.index_from_id:
            src_parent_index: QModelIndex = self.index_from_id[src_parent.id]
        else:
            if src_parent is self.super_root:
                src_parent_index = QModelIndex()
            else:
                return False
        src_row = src_item.row()

        if src_parent is dst_parent:
            if src_row < dst_row:
                dst_row -= 1
            if src_row == dst_row:
                return False
            elif abs(src_row - dst_row) == 1:
                if src_row < dst_row:
                    src_row, dst_row = dst_row, src_row
                self.beginMoveRows(parent_index, src_row, src_row, parent_index, dst_row)
                self.moveRow(parent_index, src_row, parent_index, dst_row)
                self.endMoveRows()

                self.data_changed.emit()
                return True

        self.beginMoveRows(src_parent_index, src_row, src_row, parent_index, dst_row)
        src_parent.children.pop(src_row)
        dst_parent.children.insert(dst_row, src_item)
        src_item.parent = dst_parent
        self.endMoveRows()

        self.data_changed.emit()
        return True

    # -----------------------------------------------
    # 5. Tree iteration helpers
    # -----------------------------------------------

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
        root = QModelIndex()
        return self.iterate(root, func)
