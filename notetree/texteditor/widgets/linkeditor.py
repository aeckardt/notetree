from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton)

from notetree.common.utils.settings import settings

class LinkEditorDialog(QDialog):
    def __init__(self, title: str, parent: QWidget = None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        captionLayout = QVBoxLayout()
        captionLayout.setContentsMargins(0, 0, 0, 0)
        captionLayout.setSpacing(5)

        captionLayout.addWidget(QLabel('Angezeigter Text'))

        self.caption_edit = QLineEdit()
        captionLayout.addWidget(self.caption_edit)

        layout.addLayout(captionLayout)

        linkUrlLayout = QVBoxLayout()
        linkUrlLayout.setContentsMargins(0, 0, 0, 0)
        linkUrlLayout.setSpacing(5)

        linkUrlLayout.addWidget(QLabel('URL'))

        self.link_url_edit = QLineEdit()
        linkUrlLayout.addWidget(self.link_url_edit)

        layout.addSpacing(10)
        layout.addLayout(linkUrlLayout)

        buttonLayout = QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.setSpacing(5)

        buttonLayout.addStretch(1)

        okButton = QPushButton("Ok")
        okButton.clicked.connect(self.accept)
        okButton.setMinimumWidth(120)
        buttonLayout.addWidget(okButton)

        cancelButton = QPushButton("Abbrechen")
        cancelButton.clicked.connect(self.reject)
        cancelButton.setMinimumWidth(120)
        buttonLayout.addWidget(cancelButton)

        layout.addSpacing(20)
        layout.addStretch(1)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.setWindowTitle(title)

        settings.restore_geometry(self)

    def accept(self):
        settings.save_geometry(self)
        super().accept()

    def reject(self):
        settings.save_geometry(self)
        super().reject()
