from PyQt6.QtCore import (QAbstractTableModel, pyqtSlot, Qt)
from PyQt6.QtGui import (QImage, QKeyEvent)
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QTableView, QTableWidget,
                             QAbstractItemView, QMessageBox, QLabel, QGroupBox)

from notetree.common.widgets.gradientbutton import GradientButton

class TableButtonWidget(QWidget):
    class Button(int):
        AddButton = 1
        RemoveButton = 2
        EditButton = 3

    class Flag(int):
        ConfirmationPrompt = 1
        DoubleClickEdit = 2
        KeypressActions = 4
        TabNextChild = 16

    def __init__(self, title: str, model: QAbstractTableModel = None, useGroupBox: bool = False,
                 flags: list[Flag] = [Flag.ConfirmationPrompt, Flag.DoubleClickEdit,
                                      Flag.KeypressActions, Flag.TabNextChild],
                 parent = None):
        super().__init__(parent)

        self.buttons = []

        # Use buttons depending on if handler methods are overriden
        if type(self).add_row != TableButtonWidget.add_row:
            self.buttons.append(TableButtonWidget.Button.AddButton)

        if type(self).remove_row != TableButtonWidget.remove_row:
            self.buttons.append(TableButtonWidget.Button.RemoveButton)

        if type(self).edit_row != TableButtonWidget.edit_row:
            self.buttons.append(TableButtonWidget.Button.EditButton)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if useGroupBox:
            self.groupbox = QGroupBox(title)
            layout.addWidget(self.groupbox)
        else:
            layout.addWidget(QLabel(title))

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(3)

        if model is None:
            self.table = QTableWidget()
        else:
            self.table = QTableView()
            self.table.setModel(model)
        self.model = model

        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(True)
        self.setStyleSheet('QTableView::item {border-right: 1px solid #efefef; border-bottom: 1px solid #efefef; }')

        if TableButtonWidget.Button.EditButton in self.buttons and self.Flag.DoubleClickEdit in flags:
            self.table.doubleClicked.connect(self._on_double_clicked)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        if TableButtonWidget.Flag.TabNextChild or TableButtonWidget.Flag.KeypressActions in flags:
            self.table.keyPressEvent = self._table_keypress_event
        sub_layout.addWidget(self.table)

        self.selected_row = -1

        if self.buttons != []:
            button_layout = QVBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(2)

            if TableButtonWidget.Button.AddButton in self.buttons:
                self.add_button = GradientButton(QImage("icons/fugue/plus.png", "PNG"))
                self.add_button.clicked.connect(self._on_add_clicked)
                self.add_button.setToolTip('Neuer Eintrag (Strg+N)')
                button_layout.addWidget(self.add_button)

            if TableButtonWidget.Button.RemoveButton in self.buttons:
                self.remove_button = GradientButton(QImage("icons/fugue/minus.png", "PNG"))
                self.remove_button.clicked.connect(self._on_remove_clicked)
                self.remove_button.setToolTip('Eintrag löschen (Strg+D)')
                button_layout.addWidget(self.remove_button)

            if TableButtonWidget.Button.EditButton in self.buttons:
                self.edit_button = GradientButton(QImage("icons/fugue/pencil.png", "PNG"))
                self.edit_button.clicked.connect(self._on_edit_clicked)
                self.edit_button.setToolTip('Eintrag bearbeiten (Strg+E)')
                button_layout.addWidget(self.edit_button)

            button_layout.addStretch(1)
            sub_layout.addLayout(button_layout)

        if useGroupBox:
            self.groupbox.setLayout(sub_layout)
        else:
            layout.addLayout(sub_layout)
        self.setLayout(layout)

        self.setFocusProxy(self.table)

        self.flags = flags

        self._update_enabled_status()

    # Overrideable methods
    def add_row(self):
        pass

    def remove_row(self):
        pass

    def edit_row(self):
        pass

    def update_row(self, row):
        top_left = self.table.model().index(row, 0)
        bottom_right = self.table.model().index(row, self._column_count() - 1)
        self.table.dataChanged(top_left, bottom_right)

    @pyqtSlot()
    def update_selection(self):
        self._on_selection_changed()

    def _column_count(self):
        if self.table.model() is None:
            return 0
        # Put positional argument here (even it has a default parameter)
        # Otherwise the code will crash
        return self.table.model().columnCount(...)

    @pyqtSlot()
    def _on_add_clicked(self):
        self.add_row()
        self._update_enabled_status()

    @pyqtSlot()
    def _on_remove_clicked(self):
        if self.Flag.ConfirmationPrompt in self.flags:
            # Prompt for confirmation
            msgbox = QMessageBox(self.window())
            msgbox.setWindowTitle("Bestätigung")
            msgbox.setText("Wollen Sie den Eintrag wirklich löschen?")
            msgbox.setStandardButtons(QMessageBox.StandardButton.Yes)
            msgbox.addButton(QMessageBox.StandardButton.No)
            msgbox.button(QMessageBox.StandardButton.Yes).setText("Ja")
            msgbox.button(QMessageBox.StandardButton.No).setText("Nein")
            msgbox.setDefaultButton(QMessageBox.StandardButton.Yes)
            if msgbox.exec() == QMessageBox.StandardButton.No:
                return

        self.remove_row()
        self._on_selection_changed()
        self._update_enabled_status()

    @pyqtSlot()
    def _on_edit_clicked(self):
        self.edit_row()
        self._update_enabled_status()

    @pyqtSlot()
    def _on_double_clicked(self):
        if self.edit_button.isEnabled():
            self._on_edit_clicked()

    @pyqtSlot()
    def _on_selection_changed(self):
        row = -1
        selection = self.table.selectedIndexes()
        if selection is not None and len(selection) > 0:
            row = selection[0].row()

        if self.selected_row != row:
            self.selected_row = row
            self._update_enabled_status()

    def _rowCount(self):
        if self.table.model() is None:
            return 0
        return self.table.model().rowCount()

    def _table_keypress_event(self, event : QKeyEvent):
        if event.key() == Qt.Key.Key_Tab:
            if self.Flag.TabNextChild in self.flags:
                self.focusNextChild()
                return
        elif event.key() == Qt.Key.Key_Backtab:
            if self.Flag.TabNextChild in self.flags:
                self.focusPreviousChild()
                return
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.Flag.KeypressActions in self.flags:
                key_map = {
                    Qt.Key.Key_N: [self.Button.AddButton, self._on_add_clicked],
                    Qt.Key.Key_D: [self.Button.RemoveButton, self._on_remove_clicked],
                    Qt.Key.Key_E: [self.Button.EditButton, self._on_edit_clicked]
                }
                if event.key() in key_map:
                    button, slot_fnc = key_map[event.key()]
                    if button in self.buttons:
                        if button == self.Button.AddButton:
                            if self.add_button.isEnabled():
                                slot_fnc()
                        elif button == self.Button.RemoveButton:
                            if self.remove_button.isEnabled():
                                slot_fnc()
                        elif button == self.Button.EditButton:
                            if self.edit_button.isEnabled():
                                slot_fnc()
                    return

        QTableView.keyPressEvent(self.table, event)

    def _update_enabled_status(self):
        row = self.selected_row
        if self.Button.RemoveButton in self.buttons:
            self.remove_button.setEnabled(row != -1)
        if self.Button.EditButton in self.buttons:
            self.edit_button.setEnabled(row != -1)
