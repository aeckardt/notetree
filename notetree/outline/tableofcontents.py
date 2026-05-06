from PyQt6.QtCore import (QModelIndex, Qt, QItemSelectionModel, pyqtSlot, pyqtSignal)
from PyQt6.QtGui import (QTextDocument)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QAbstractItemView)

from notetree.outline.model import OutlineModel
from notetree.outline.treeview import OutlineTreeView

class TableOfContents(QWidget):
    selection_changed = pyqtSignal(QModelIndex, QModelIndex)

    def __init__(self, window_title: str, parent: QWidget = None):
        QWidget.__init__(self, parent)

        self.setWindowTitle(window_title)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(QLabel(window_title))

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(3)

        self.model = OutlineModel()
        self.model.loaded.connect(self._on_loaded)

        self.treeview = OutlineTreeView()
        self.treeview.setModel(self.model)

        self.treeview.setHeaderHidden(True)
        self.treeview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.treeview.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.treeview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.treeview.setUniformRowHeights(True)
        self.setStyleSheet('QTreeView::item {border-right: 1px solid #efefef; border-bottom: 1px solid #efefef; }')

        self.treeview.doubleClicked.connect(self._on_doubleclicked)
        self.treeview.selectionModel().selectionChanged.connect(self._on_selectionchanged, Qt.ConnectionType.DirectConnection)

        sub_layout.addWidget(self.treeview)

        self.selected_index = QModelIndex()

        layout.addLayout(sub_layout)
        self.setLayout(layout)

        self.setFocusProxy(self.treeview)

    def clear(self):
        self.model.clear()

    def set_text_document(self, document: QTextDocument = None):
        self.model.load_document(document)

    def update_row(self, row):
        top_left = self.treeview.model().index(row, 0)
        bottom_right = self.treeview.model().index(row, self._column_count() - 1)
        self.treeview.dataChanged(top_left, bottom_right)

    def _column_count(self):
        if self.treeview.model() is None:
            return 0
        return self.treeview.model().columnCount()

    @pyqtSlot()
    def _on_loaded(self):
        self.treeview.expandAll()

    @pyqtSlot()
    def _on_doubleclicked(self):
        # Navigate to the heading
        pass

    @pyqtSlot()
    def _on_selectionchanged(self):
        selection = self.treeview.selectedIndexes()
        if selection is None or len(selection) == 0:
            return

        if selection[0] != self.selected_index:
            deselected_index = self.selected_index

            self.selected_index = selection[0]

            self.selection_changed.emit(self.selected_index, deselected_index)

    def _row_count(self):
        if self.model is None or not self.selected_index.parent().isValid():
            return 0
        return self.model.rowCount(self.selected_index.parent())

    def _select_index(self, index):
        command = QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows
        self.treeview.selectionModel().select(index, command)
        self.selected_index = index

    def _swap_neighbors(self, row1, row2):
        if row1 < row2:
            row1, row2 = row2, row1
        parent_index = self.selected_index.parent()

        self.model.beginMoveRows(parent_index, row1, row1, parent_index, row2)
        self.model.moveRow(parent_index, row1, parent_index, row2)
        self.model.endMoveRows()
