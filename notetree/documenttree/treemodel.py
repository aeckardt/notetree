from dataclasses import dataclass, field

from PyQt6.QtCore import (QModelIndex, QAbstractItemModel, QObject, pyqtSignal, Qt, QByteArray,
                          QDataStream, QIODevice, QMimeData)

from notetree.project.file import ProjectFile

@dataclass
class DocumentNode:
    """
    Represents a node for one document in the project.
    That includes its displayed name, icon and links (parent, children) to other documents.

    The document text itself is stored as markdown string.
    """

    # The unique ID is used to identify the document
    id: int | None = None

    # Name and icon of the document are visible in the treeview
    displayed_name: str = ''
    icon_index: int | None = None

    # Since documents are organized hierarchically in a tree,
    # they are also nodes (potentially) with a parent and children.
    parent: "DocumentNode | None" = None
    children: list["DocumentNode"] = field(default_factory=list)

    # Expanded state of treeview node
    is_expanded: bool = True

    # Markdown string of document text
    markdown: str = ''

    def is_ancestor_of(self, other: "DocumentNode") -> bool:
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
    inserted = pyqtSignal(int)
    removed = pyqtSignal(list)
    tree_changed = pyqtSignal()

    # -----------------------------------------------
    # 1. Standard TreeModel handlers (add, remove, ...)
    # -----------------------------------------------

    def __init__(self, parent: QObject | None = None):
        QAbstractItemModel.__init__(self, parent)

        # Invisible root above top level nodes (= "roots")
        self._invisible_root = DocumentNode()

        # Next unused unique document ID
        self._next_id = 1

        # Mapping of document ID to node for quick access
        self._node_from_id: dict[int, DocumentNode] = {}

    def insert_child_node(self, node: DocumentNode, parent: QModelIndex):
        parent_node = self.node_from_index(parent)

        row = len(parent_node.children)

        self.beginInsertRows(parent, row, row)
        if node.id is None:
            node.id = self.generate_id()
        self._node_from_id[node.id] = node
        node.parent = parent_node
        parent_node.children.append(node)
        self.endInsertRows()

        self.tree_changed.emit()
        self.inserted.emit(node.id)

    def columnCount(self, _):
        return 1

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        if not index.isValid():
            return None

        node: DocumentNode = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return node.displayed_name
        elif role == ITEM_ICON_ROLE:
            return node.icon_index

        return None

    def flags(self, index: QModelIndex):
        if index.isValid():
            return QAbstractItemModel.flags(self, index)
        else:
            return Qt.ItemFlag.NoItemFlags

    def index(self, row: int, column: int, parent: QModelIndex):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_node = self.node_from_index(parent)
        child_node = parent_node.children[row]

        return self.createIndex(row, column, child_node)

    def node_from_index(self, index: QModelIndex) -> DocumentNode:
        if not index.isValid():
            return self._invisible_root
        return index.internalPointer()

    def index_from_node(self, node: DocumentNode) -> QModelIndex:
        if node is None or node is self._invisible_root:
            return QModelIndex()
        return self.createIndex(node.row(), 0, node)

    def moveRow(self, source_parent: QModelIndex, source_row: int,
                destination_parent: QModelIndex, destination_child: int):
        if source_parent != destination_parent:
            return False

        parent_node: DocumentNode = source_parent.internalPointer()
        if parent_node is not None:
            parent_node.swap(source_row, destination_child)
        else:
            self._invisible_root.swap(source_row, destination_child)

        self.tree_changed.emit()

        return True

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        node: DocumentNode = index.internalPointer()
        parent_node = node.parent

        if parent_node is None or parent_node is self._invisible_root:
            return QModelIndex()

        return self.createIndex(parent_node.row(), 0, parent_node)

    def remove_node(self, index: QModelIndex):
        if not index.isValid():
            raise Exception('Invalid node cannot be removed')

        node: DocumentNode = index.internalPointer()
        if index.parent().isValid():
            parent_index = index.parent()
            parent_node = parent_index.internalPointer()
        elif self._invisible_root is not None:
            parent_index = QModelIndex()
            parent_node = self._invisible_root
        else:
            raise Exception('Cannot remove node without a root node')

        row = node.row()

        # Remove node from tree structure
        self.beginRemoveRows(parent_index, row, row)
        parent_node.children.pop(row)
        self.endRemoveRows()

        # Emit tree changed signal for update of treeview
        self.tree_changed.emit()

        # Emit removed signal with list of all removed document IDs (including subtree)
        def subtree_ids(node: DocumentNode) -> list[int]:
            ids = [node.id]
            for child in node.children:
                ids.extend(subtree_ids(child))
            return ids
        self.removed.emit(subtree_ids(node))

    def rowCount(self, parent: QModelIndex):
        if parent.column() > 0:
            return 0

        parent_node = self.node_from_index(parent)
        return len(parent_node.children)

    def update_index(self, index: QModelIndex):
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, ITEM_ICON_ROLE])

    # -----------------------------------------------
    # 2. ID handlers
    # -----------------------------------------------

    def generate_id(self) -> int:
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def root_ids(self):
        if self._invisible_root is None:
            return []

        ids = []
        root_count = len(self._invisible_root.children)
        for row in range(root_count):
            child_id = self._invisible_root.children[row].id
            ids.append(child_id)

        return ids

    # -----------------------------------------------
    # 3. Import / Export data
    # -----------------------------------------------

    def import_data(self, project: ProjectFile):
        self.beginResetModel()

        # Reset tree structure with new root
        self._invisible_root = DocumentNode()
        self._next_id = project.next_id

        # Reset mapping of document ID to node
        self._node_from_id.clear()

        # Generate list of all document IDs (ordered by their index in "project.documents")
        document_ids: list[int] = []
        for doc in project.documents:
            document_ids.append(doc['id'])

        def integrate_node(doc_id: int, parent_node: DocumentNode):
            """
            Integrate tree nodes recursively.
            """
            # Get dataset with specified ID from list
            node_record = project.documents[document_ids.index(doc_id)]

            # Build node (= DocumentMetadata object) from this dataset
            node = DocumentNode(node_record['id'], node_record['description'], node_record.get('icon'), parent_node)
            if 'expanded' in node_record:
                node.is_expanded = node_record['expanded']
            if 'notes' in node_record:
                node.markdown = '\n'.join(node_record['notes'])

            # Add children (if available)
            if 'children' in node_record:
                for child_id in node_record['children']:
                    if not child_id in document_ids:
                        raise Exception('Document referenced by id not found.')
                    integrate_node(child_id, node)

            # Add node to mapping
            self._node_from_id[node.id] = node

            # Link node to parent
            parent_node.children.append(node)

        # Build tree
        # Start with top level "root" nodes (under invisible super root) 
        for root_id in project.root_ids:
            if not root_id in document_ids:
                raise Exception('Root referenced by id not found.')
            integrate_node(root_id, self._invisible_root)

        self.endResetModel()

        self.loaded.emit()

    def export_data(self, project: ProjectFile):
        # Clear data before export
        project.documents = []
        project.root_ids = []
        project.next_id = self._next_id

        def add_dataset(parent_node: DocumentNode, row: int, parent_record: dict = None):
            """
            Build flat list recursively from tree.
            """
            # Get node from children list
            node = parent_node.children[row]

            # Add node ID to parent dataset
            if parent_record is None:
                # No (visible) parent, add ID to "roots"
                project.root_ids.append(node.id)
            else:
                if 'children' not in parent_record:
                    parent_record['children'] = []
                parent_record['children'].append(node.id)

            # Build dataset (dict) from DocumentNode object
            node_record = {'description': node.displayed_name, 'id': node.id}
            if not node.is_expanded:
                node_record['expanded'] = node.is_expanded
            if node.icon_index is not None:
                node_record['icon'] = node.icon_index
            if node.markdown is not None and len(node.markdown) > 0:
                node_record['notes'] = node.markdown.splitlines()

            # Add dataset to documents list
            project.documents.append(node_record)

            # Add children (if available)
            child_count = len(node.children)
            for row in range(child_count):
                add_dataset(node, row, node_record)

        # Add all documents, starting with roots
        root_count = len(self._invisible_root.children)
        for row in range(root_count):
            add_dataset(self._invisible_root, row)

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
        source_index: QModelIndex = indexes[0]
        source_node: DocumentNode = source_index.internalPointer()

        ba = QByteArray()
        stream = QDataStream(ba, QIODevice.OpenModeFlag.WriteOnly)
        stream.writeInt32(source_node.id)

        md = QMimeData()
        md.setData(MIME_TYPE, ba)
        return md

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent_index: QModelIndex):
        if action != Qt.DropAction.MoveAction:
            return False
        if not data or not data.hasFormat(MIME_TYPE):
            return False

        if parent_index.isValid():
            new_parent_node: DocumentNode = parent_index.internalPointer()
        else:
            new_parent_node = self._invisible_root

        # The given row is where the node should be inserted
        # It is -1, when no row is specified

        if row == -1:
            new_row = len(new_parent_node.children)
        else:
            new_row = row

        # Determine source
        ba = data.data(MIME_TYPE)
        stream = QDataStream(ba, QIODevice.OpenModeFlag.ReadOnly)
        doc_id = stream.readInt32()

        # Determine source node and old parent node
        source_node = self._node_from_id.get(doc_id)
        if source_node is None:
            return False
        old_parent_node: DocumentNode = source_node.parent
        if old_parent_node is None:
            return False

        # Don't drop into itself / own ancestors
        if source_node.is_ancestor_of(new_parent_node):
            return False

        # Determine old parent index
        old_parent_index = self.index_from_node(old_parent_node)
        source_row = source_node.row()

        # If old and new parent are the same
        # Only move the node within the children list of this parent
        if old_parent_node is new_parent_node:
            if source_row < new_row:
                new_row -= 1
            if source_row == new_row:
                return False
            elif abs(source_row - new_row) == 1:
                if source_row < new_row:
                    source_row, new_row = new_row, source_row
                self.beginMoveRows(parent_index, source_row, source_row, parent_index, new_row)
                self.moveRow(parent_index, source_row, parent_index, new_row)
                self.endMoveRows()

                self.tree_changed.emit()
                return True

        # Move node to new parent
        self.beginMoveRows(old_parent_index, source_row, source_row, parent_index, new_row)
        old_parent_node.children.pop(source_row)
        new_parent_node.children.insert(new_row, source_node)
        source_node.parent = new_parent_node
        self.endMoveRows()

        # Emit tree changed signal for modification state
        self.tree_changed.emit()
        return True

    # -----------------------------------------------
    # 5. Tree iteration helpers
    # -----------------------------------------------

    def iterate(self, func):
        root = QModelIndex()
        return self._iterate(root, func)

    def _iterate(self, index: QModelIndex, func, depth = 0):
        if index.isValid():
            func(index)

        if not self.hasChildren(index):
            return

        row_count = self.rowCount(index)
        column_count = self.columnCount(index)

        for row in range(row_count):
            for column in range(column_count):
                self._iterate(self.index(row, column, index), func, depth + 1)

    def iterate_nodes(self, func):
        root = self._invisible_root
        return self._iterate_nodes(root, func)

    def _iterate_nodes(self, node: DocumentNode, func, depth = 0):
        if node is not self._invisible_root:
            func(node)

        for child in node.children:
            self._iterate_nodes(child, func, depth + 1)
