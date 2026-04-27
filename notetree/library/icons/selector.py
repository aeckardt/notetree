from PyQt6.QtCore import (pyqtSlot, Qt)
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QHeaderView, QAbstractItemView, QPushButton,
                             QHBoxLayout)

from notetree.common.utils.errormessage import show_error_msg
from notetree.common.utils.settings import settings
from notetree.common.widgets.tablebuttonwidget import TableButtonWidget
from notetree.library.icons.model import IconModel

# IconSelectorDialog
# Available Filters:
# -> Name Filter
# Can be initialized with specific name
# Option to select empty name (field is '(leer)')

class IconSelectorDialog(QDialog):
    def __init__(self, title, selected_index = None, allow_empty: bool = False):
        super().__init__()

        self.setMinimumSize(650, 280)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(QLabel("Suchfilter"))
        self.line_edit = QLineEdit()
        self.line_edit.textChanged.connect(self._load_contents)
        layout.addWidget(self.line_edit)

        layout.addSpacing(15)

        layout.addWidget(QLabel("Icons"))

        self.icons_model = IconModel()
        self.tablewidget = TableButtonWidget('Icons', self.icons_model)
        self.table = self.tablewidget.table

        self.table.setMinimumSize(350, 200)
        self.table.horizontalHeader().resizeSection(0, 220)
        self.table.horizontalHeader().resizeSection(1, 110)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._on_doubleclicked)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        layout.addSpacing(15)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)
        button_layout.addStretch(1)
        ok_button = QPushButton("Ok")
        ok_button.clicked.connect(self.accept)
        ok_button.setMinimumWidth(120)
        button_layout.addWidget(ok_button)
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setMinimumWidth(120)
        button_layout.addWidget(cancel_button)

        layout.addSpacing(20)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle(title)

        self.allow_empty = allow_empty
        self.icon_index = selected_index
        self._load_contents()
        settings.restore_geometry(self)

    def accept(self):
        if self.selected_row == -1:
            if self.icons_model.rowCount() == 1:
                self.selected_row = 0
                self.icon_index = self.icons_model.item_at(0)['index']
            else:
                show_error_msg('Es wurde kein Icon ausgewählt', self)
                return

        settings.save_geometry(self)
        super().accept()

    def reject(self):
        settings.save_geometry(self)
        super().reject()

    def _load_contents(self):
        # Filter contents by search string
        filter_str = self.line_edit.text().lower()
        self.icons_model.filter(lambda icon: filter_str in icon['name'].lower())

        # Sort contents by name
        self.icons_model.sort(0, Qt.SortOrder.AscendingOrder)

        # Update selected row (keep index, if possible)
        self.selected_row = -1
        for row in range(self.icons_model.rowCount()):
            icon = self.icons_model.item_at(row)
            if icon['index'] == self.icon_index:
                self.table.selectRow(row)
                self.selected_row = row
                break

    @pyqtSlot()
    def _on_doubleclicked(self):
        self.accept()

    @pyqtSlot()
    def _on_selection_changed(self):
        row = -1
        selection = self.table.selectedIndexes()
        if selection is not None and len(selection) > 0:
            row = selection[0].row()

        if self.selected_row != row:
            self.selected_row = row
        
        if self.selected_row < 0 or self.selected_row >= self.icons_model.rowCount():
            self.icon_index = None
        else:
            self.icon_index = self.icons_model.item_at(self.selected_row)['index']
