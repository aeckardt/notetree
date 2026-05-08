from PyQt6.QtCore import (Qt)
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHeaderView)

from notetree.common.utils.settings import settings
from notetree.library.icons.model import IconModel
from notetree.library.icons.tablewidget import IconTableWidget

class IconManagerDialog(QDialog):
    def __init__(self, window_title):
        QDialog.__init__(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.icons_model = IconModel()
        self.icons_tablewidget = IconTableWidget(self.icons_model)
        self.icons_model.sort(0, Qt.SortOrder.AscendingOrder)
        self.icons_model.sort(1, Qt.SortOrder.AscendingOrder)

        self.icons_table = self.icons_tablewidget.table
        self.icons_table.horizontalHeader().resizeSection(0, 220)
        self.icons_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.icons_table.horizontalHeader().setSortIndicator(1, Qt.SortOrder.AscendingOrder)

        layout.addWidget(self.icons_tablewidget)

        self.setLayout(layout)

        self.icons_table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self.selectedRow = -1

        self.setWindowTitle(window_title)
        self.setMinimumSize(600, 450)

        # The flag is set while the previous selection is restored
        self._ignoreSelectionChangedSignal = False

        settings.restore_geometry(self)

    def accept(self):
        settings.save_geometry(self)
        super().accept()

    def reject(self):
        settings.save_geometry(self)
        super().reject()

    def _on_selection_changed(self):
        # If the flag is set, don't process the selection change
        if self._ignoreSelectionChangedSignal:
            return

        row = -1
        selection = self.icons_table.selectedIndexes()
        if selection is not None and len(selection) > 0:
            row = selection[0].row()

        if self.selectedRow != row:
            self.selectedRow = row
            self.icons_tablewidget.update_selection()
