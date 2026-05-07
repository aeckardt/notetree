import os

from PyQt6.QtCore import (Qt, QMargins)
from PyQt6.QtGui import (QPixmap)
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton)

from notetree.common.utils.settings import settings
from notetree.common.widgets.gradientbutton import GradientButton
from notetree.documenttree.treemodel import DocumentNode
from notetree.library.icons.datacontainer import icons
from notetree.library.icons.selector import IconSelectorDialog

class DocumentNodeEditorDialog(QDialog):
    def __init__(self, window_title: str, node: DocumentNode, parent: QWidget = None):
        QDialog.__init__(self, parent)

        self.setMinimumSize(450, 70)

        self.node = node

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        description_label = QLabel('Beschreibung')
        layout.addWidget(description_label)
        self.description_edit = QLineEdit()
        layout.addWidget(self.description_edit)
        layout.addSpacing(10)

        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(5)

        widget_layout = QHBoxLayout()
        widget_layout.setContentsMargins(2, 0, 0, 0)
        widget_layout.setSpacing(3)

        self.icon_frame = QLabel()
        self.icon_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget_layout.addWidget(self.icon_frame)

        self.icon_name = QLabel()
        self.icon_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        widget_layout.addWidget(self.icon_name, 1)

        self.icon_widget = QWidget()
        self.icon_widget.setObjectName('iconwidget')
        self.icon_widget.setStyleSheet('QWidget#iconwidget { background: white; border: 1px solid #bfbfbf; }')
        self.icon_widget.setLayout(widget_layout)

        icon_layout.addWidget(self.icon_widget)

        self.select_button = GradientButton(text=' Auswählen ')
        self.select_button.clicked.connect(self._on_select_clicked)
        icon_layout.addWidget(self.select_button)

        self.remove_button = GradientButton(text=' Löschen ')
        self.remove_button.clicked.connect(self._on_remove_clicked)
        icon_layout.addWidget(self.remove_button)

        layout.addWidget(QLabel('Icon'))
        layout.addLayout(icon_layout)

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

        layout.addStretch(1)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle(window_title)

        self._load_contents()
        settings.restore_geometry(self)

    def accept(self):
        # Copy editor content back to given dataset
        self._save_contents()

        settings.save_geometry(self)
        super().accept()

    def reject(self):
        settings.save_geometry(self)
        super().reject()

    def _load_contents(self):
        # Set description
        self.description_edit.setText(self.node.displayed_name)

        # Set icon
        self.icon_index = self.node.icon_index
        self._update_icon()

    def _on_remove_clicked(self):
        self.icon_index = None
        self._update_icon()

    def _on_select_clicked(self):
        isd = IconSelectorDialog('Icon auswählen', self.icon_index, allow_empty=True)
        if isd.exec() == QDialog.DialogCode.Accepted:
            self.icon_index = isd.icon_index
            self._update_icon()

    def _save_contents(self):
        self.node.displayed_name = self.description_edit.text()
        self.node.icon_index = self.icon_index

    def _update_icon(self):
        if self.icon_index is not None:
            icon = icons.from_index(self.icon_index)
            filename = f'{os.getcwd()}/icons/{icon['path']}'

            pixmap = QPixmap(filename, 'PNG')
            if pixmap.height() > 24:
                pixmap = pixmap.scaledToHeight(24)
            self.icon_frame.setPixmap(pixmap)
            self.icon_frame.setFixedSize(pixmap.size().grownBy(QMargins(2, 2, 2, 2)))

            self.icon_name.setText(icon['name'])
        else:
            self.icon_frame.clear()
            self.icon_name.clear()
