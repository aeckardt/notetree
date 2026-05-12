from PyQt6.QtCore import (QModelIndex, QItemSelectionModel, Qt, pyqtSlot, pyqtSignal, QRect)
from PyQt6.QtGui import (QImage, QMouseEvent)
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QAbstractItemView,
                             QDialog, QMessageBox, QTreeView, QStyle, QStyleOptionViewItem)

from notetree.common.widgets.gradientbutton import GradientButton
from notetree.documenttree.nodeeditor import DocumentNodeEditorDialog
from notetree.documenttree.treemodel import DocumentNode, DocumentTreeModel
from notetree.documenttree.treeview import DocumentTreeView

class DocumentTreeWidget(QWidget):
    class Button(int):
        AddButton = 1
        RemoveButton = 2
        EditButton = 3
        MoveUpButton = 4
        MoveDownButton = 5

    class Flag(int):
        ConfirmationPrompt = 1

    selection_changed = pyqtSignal(QModelIndex, QModelIndex)

    def __init__(self, title: str, use_groupbox: bool = False,
                 flags: list[Flag] = [Flag.ConfirmationPrompt],
                 model: DocumentTreeModel = None, parent = None):
        super().__init__(parent)

        self.buttons = []

        # Use buttons depending on if handler methods are overriden
        # if type(self).addRow != TreeButtonWidget.addRow:
        self.buttons.append(DocumentTreeWidget.Button.AddButton)

        # if type(self).removeRow != TreeButtonWidget.removeRow:
        self.buttons.append(DocumentTreeWidget.Button.RemoveButton)

        # if type(self).editRow != TreeButtonWidget.editRow:
        self.buttons.append(DocumentTreeWidget.Button.EditButton)

        # if type(self).moveUpRow != TreeButtonWidget.moveUpRow:
        self.buttons.append(DocumentTreeWidget.Button.MoveUpButton)

        # if type(self).moveDownRow != TreeButtonWidget.moveDownRow:
        self.buttons.append(DocumentTreeWidget.Button.MoveDownButton)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if use_groupbox:
            self.groupbox = QGroupBox(title)
            layout.addWidget(self.groupbox)
        else:
            layout.addWidget(QLabel(title))

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(3)

        if model is None:
            self.model = DocumentTreeModel()
        else:
            self.model = model
        self.model.loaded.connect(self._on_model_loaded)

        self.treeview = DocumentTreeView()
        self.treeview.setModel(self.model)

        self.treeview.setHeaderHidden(True)
        self.treeview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.treeview.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.treeview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.treeview.setUniformRowHeights(True)
        self.treeview.setItemsExpandable(True)

        self.treeview.setDragEnabled(True)
        self.treeview.setAcceptDrops(True)
        self.treeview.setDropIndicatorShown(True)
        self.treeview.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.treeview.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        # Override behavior for double click on view
        self.treeview.mouseDoubleClickEvent = self._treeview_mouse_doubleclick_event

        self.setStyleSheet('QTreeView::item {border-right: 1px solid #efefef; border-bottom: 1px solid #efefef; }')

        self.treeview.selectionModel().selectionChanged.connect(self._on_selection_changed, Qt.ConnectionType.DirectConnection)
        sub_layout.addWidget(self.treeview)

        self.selected_index = QModelIndex()

        if self.buttons != []:
            button_layout = QVBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(2)

            if DocumentTreeWidget.Button.AddButton in self.buttons:
                self.add_button = GradientButton(QImage("icons/fugue/plus.png", "PNG"))
                self.add_button.clicked.connect(self._on_add_clicked)
                self.add_button.setToolTip(self.tr("Insert node (Ctrl+N)"))
                button_layout.addWidget(self.add_button)

            if DocumentTreeWidget.Button.RemoveButton in self.buttons:
                self.remove_button = GradientButton(QImage("icons/fugue/minus.png", "PNG"))
                self.remove_button.clicked.connect(self._on_remove_clicked)
                self.remove_button.setToolTip(self.tr("Remove node (Ctrl+D)"))
                button_layout.addWidget(self.remove_button)

            if DocumentTreeWidget.Button.EditButton in self.buttons:
                self.edit_button = GradientButton(QImage("icons/fugue/pencil.png", "PNG"))
                self.edit_button.clicked.connect(self._on_edit_clicked)
                self.edit_button.setToolTip(self.tr("Edit node (Ctrl+E)"))
                button_layout.addWidget(self.edit_button)

            if DocumentTreeWidget.Button.MoveUpButton in self.buttons:
                self.moveup_button = GradientButton(QImage("icons/fugue/arrow-090.png", "PNG"))
                self.moveup_button.clicked.connect(self._on_moveup_clicked)
                self.moveup_button.setToolTip(self.tr("Swap with neighbor above (Ctrl+Up)"))
                button_layout.addWidget(self.moveup_button)

            if DocumentTreeWidget.Button.MoveDownButton in self.buttons:
                self.movedown_button = GradientButton(QImage("icons/fugue/arrow-270.png", "PNG"))
                self.movedown_button.clicked.connect(self._on_movedown_clicked)
                self.movedown_button.setToolTip(self.tr("Swap with neighbor below (Ctrl+Down)"))
                button_layout.addWidget(self.movedown_button)

            button_layout.addStretch(1)
            sub_layout.addLayout(button_layout)

        if use_groupbox:
            self.groupbox.setLayout(sub_layout)
        else:
            layout.addLayout(sub_layout)
        self.setLayout(layout)

        self.setFocusProxy(self.treeview)

        self.flags = flags

        self._update_enabled_status()

    # Overrideable methods
    def add_row(self):
        new_node = DocumentNode()
        ned = DocumentNodeEditorDialog(self.tr("Insert node"), new_node)
        if ned.exec() == QDialog.DialogCode.Accepted:
            self.model.insert_child_node(new_node, self.selected_index)

            # Set the parent node as expanded
            # This makes sure the child node is visible after inserting
            self.treeview.setExpanded(self.selected_index, True)

            # Select the new node after insertion
            ModelSelectionFlag = QItemSelectionModel.SelectionFlag
            command = ModelSelectionFlag.ClearAndSelect | ModelSelectionFlag.Rows
            self.treeview.selectionModel().select(self.model.index_from_node(new_node), command)

    def edit_row(self):
        node: DocumentNode = self.selected_index.internalPointer()

        editor = DocumentNodeEditorDialog(self.tr("Edit node"), node)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.model.update_index(self.selected_index)
            self.model.tree_changed.emit()

    def remove_row(self):
        self.model.remove_node(self.selected_index)

    def move_up_row(self):
        row = self.selected_index.row()
        self._swap_neighbors(row, row - 1)

    def move_down_row(self):
        row = self.selected_index.row()
        self._swap_neighbors(row, row + 1)

    def update_row(self, row):
        topLeft = self.treeview.model().index(row, 0)
        bottomRight = self.treeview.model().index(row, self._column_count() - 1)
        self.treeview.dataChanged(topLeft, bottomRight)

    def _column_count(self):
        if self.treeview.model() is None:
            return 0
        return self.treeview.model().columnCount()

    @pyqtSlot()
    def _on_add_clicked(self):
        self.add_row()
        self._update_enabled_status()

    @pyqtSlot()
    def _on_model_loaded(self):
        # Reset selected index
        self.selected_index = QModelIndex()

        # Expand all nodes with the 'expanded' flag
        def maybe_expand(index: QModelIndex):
            node = index.internalPointer()
            self.treeview.setExpanded(index, node.is_expanded)
        model: DocumentTreeModel = self.treeview.model()
        model.iterate(maybe_expand)

        self._update_enabled_status()

    @pyqtSlot()
    def _on_edit_clicked(self):
        self.edit_row()
        self._update_enabled_status()

    @pyqtSlot()
    def _on_remove_clicked(self):
        if self.Flag.ConfirmationPrompt in self.flags:
            # Prompt for confirmation
            msgbox = QMessageBox(self.window())
            msgbox.setWindowTitle(self.tr("Confirmation"))
            msgbox.setText(self.tr("Do you really want to remove the node?"))
            msgbox.setStandardButtons(QMessageBox.StandardButton.Yes)
            msgbox.addButton(QMessageBox.StandardButton.No)
            msgbox.button(QMessageBox.StandardButton.Yes).setText(self.tr("Yes"))
            msgbox.button(QMessageBox.StandardButton.No).setText(self.tr("No"))
            msgbox.setDefaultButton(QMessageBox.StandardButton.Yes)
            if msgbox.exec() == QMessageBox.StandardButton.No:
                return

        self.remove_row()
        self._on_selection_changed()
        self._update_enabled_status()

    @pyqtSlot()
    def _on_moveup_clicked(self):
        self.move_up_row()
        newIndex = self.model.index(self.selected_index.row() - 1, 0, self.selected_index.parent())
        self._select_index(newIndex)
        self._update_enabled_status()

    @pyqtSlot()
    def _on_movedown_clicked(self):
        self.move_down_row()
        new_index = self.model.index(self.selected_index.row() + 1, 0, self.selected_index.parent())
        self._select_index(new_index)
        self._update_enabled_status()

    @pyqtSlot()
    def _on_selection_changed(self):
        selection = self.treeview.selectedIndexes()
        if selection is None or len(selection) == 0:
            return

        if selection[0] != self.selected_index:
            deselectedIndex = self.selected_index

            self.selected_index = selection[0]
            self._update_enabled_status()

            self.selection_changed.emit(self.selected_index, deselectedIndex)

    def _row_count(self):
        if self.model is None:
            return 0
        return self.model.rowCount(self.selected_index.parent())

    def _select_index(self, index):
        command = QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows
        self.treeview.selectionModel().select(index, command)
        self.selected_index = index

    def _swap_neighbors(self, row1, row2):
        if row1 < row2:
            row1, row2 = row2, row1
        parentIndex = self.selected_index.parent()

        self.model.beginMoveRows(parentIndex, row1, row1, parentIndex, row2)
        self.model.moveRow(parentIndex, row1, parentIndex, row2)
        self.model.endMoveRows()

    def _disclosure_rect(self, index: QModelIndex):
        # Style-Option for the view index
        opt = QStyleOptionViewItem()
        opt.initFrom(self.treeview.viewport())
        opt.rect = self.treeview.visualRect(index)
        opt.state |= QStyle.StateFlag.State_Enabled

        if self.treeview.selectionModel() and self.treeview.selectionModel().isSelected(index):
            opt.state |= QStyle.StateFlag.State_Selected

        r = self.treeview.style().subElementRect(
            QStyle.SubElement.SE_TreeViewDisclosureItem, opt, self.treeview.viewport()
        )

        # Fallback: some styles return 0/Null here
        if not r.isValid() or r.isNull():
            depth = 0
            p = index.parent()
            while p.isValid():
                depth += 1
                p = p.parent()

            indent = self.treeview.indentation() or self.treeview.style().pixelMetric(
                QStyle.PixelMetric.PM_TreeViewIndentation, None, self.treeview
            )
            w = self.treeview.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, None, self.treeview)
            h = self.treeview.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorHeight, None, self.treeview)

            x = opt.rect.left() + depth * indent
            y = opt.rect.top() + (opt.rect.height() - h) // 2
            r = QRect(x, y, w, h)

        return r

    def _treeview_mouse_doubleclick_event(self, event: QMouseEvent):
        index: QModelIndex = self.treeview.indexAt(event.pos())
        if not index.isValid():
            return QTreeView.mouseDoubleClickEvent(self.treeview, event)

        # Test if the doubleclick is on the indicator / icon
        if not self._disclosure_rect(index).contains(event.pos()):
            # Do not open editor in this case (if possible: expand or collapse)
            return QTreeView.mouseDoubleClickEvent(self.treeview, event)

        node: DocumentNode = index.internalPointer()
        editor = DocumentNodeEditorDialog(self.tr("Edit node"), node)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.model.update_index(index)
            self.model.tree_changed.emit()

        event.accept()
        return

    def _update_enabled_status(self):
        row_count = self._row_count()

        row = self.selected_index.row()
        if self.Button.RemoveButton in self.buttons:
            self.remove_button.setEnabled(row != -1)
        if self.Button.EditButton in self.buttons:
            self.edit_button.setEnabled(row != -1)
        if self.Button.MoveUpButton in self.buttons:
            self.moveup_button.setEnabled(row > 0)
        if self.Button.MoveDownButton in self.buttons:
            self.movedown_button.setEnabled(row != -1 and row < row_count - 1)
