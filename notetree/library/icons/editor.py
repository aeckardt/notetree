import os

from PyQt6.QtCore import (Qt, QMargins)
from PyQt6.QtGui import (QPixmap)
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFileDialog, QRadioButton, QButtonGroup)

from notetree.common.utils.settings import settings
from notetree.common.widgets.gradientbutton import GradientButton

class IconEditorDialog(QDialog):
    def __init__(self, window_title, dataset):
        super().__init__()

        # Setup editor context to be used in this module
        self.dataset = dataset

        # Setup image directory
        self.base_dir = f'{os.getcwd()}/img'

        # Initialize dialog controls
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        name_layout = QVBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(5)

        name_layout.addWidget(QLabel(self.tr("Description")))
        self.name_edit = QLineEdit()
        self.name_edit.setMinimumWidth(350)
        name_layout.addWidget(self.name_edit)

        path_layout = QVBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(5)

        path_row_layout = QHBoxLayout()
        path_row_layout.setContentsMargins(0, 0, 0, 0)
        path_row_layout.setSpacing(5)

        self.path_edit = QLineEdit()
        self.path_edit.setMinimumWidth(300)
        path_row_layout.addWidget(self.path_edit)

        self.open_button = GradientButton(text='...')
        self.open_button.setFixedSize(24, 24)
        self.open_button.clicked.connect(self._open_file_clicked)
        path_row_layout.addWidget(self.open_button)

        path_layout.addWidget(QLabel(self.tr("Path")))
        path_layout.addLayout(path_row_layout)

        design_layout = QVBoxLayout()
        design_layout.setContentsMargins(0, 0, 0, 0)
        design_layout.setSpacing(5)

        design_layout.addWidget(QLabel(self.tr("Design")))

        self.button_group = QButtonGroup()
        self.standard_design_radiobutton = QRadioButton(self.tr("Standard Design"))
        self.button_group.addButton(self.standard_design_radiobutton, 0)
        self.flat_design_radiobutton = QRadioButton(self.tr("Flat Design"))
        self.button_group.addButton(self.flat_design_radiobutton, 1)
        design_layout.addWidget(self.standard_design_radiobutton)
        design_layout.addWidget(self.flat_design_radiobutton)

        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        self.preview_img = QLabel()
        self.preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_img.setStyleSheet('QLabel { border: 1px solid #dfdfdf; background: white; }')
        preview_layout.addWidget(self.preview_img, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(name_layout)

        layout.addSpacing(10)
        layout.addLayout(path_layout)

        layout.addSpacing(10)
        layout.addLayout(design_layout)

        layout.addSpacing(10)
        layout.addLayout(preview_layout)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)

        button_layout.addStretch(1)

        ok_button = QPushButton(self.tr("Ok"))
        ok_button.clicked.connect(self.accept)
        ok_button.setMinimumWidth(120)
        button_layout.addWidget(ok_button)

        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.reject)
        cancel_button.setMinimumWidth(120)
        button_layout.addWidget(cancel_button)

        layout.addStretch(1)
        layout.addSpacing(5)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle(window_title)

        self._load_contents(self.dataset)
        settings.restore_geometry(self)

    def accept(self):
        # Copy editor context back to given dataset
        self._save_contents(self.dataset)

        settings.save_geometry(self)
        super().accept()

    def reject(self):
        settings.save_geometry(self)
        super().reject()

    def _load_contents(self, icon):
        # Setup dialog controls from context
        self.name_edit.setText(icon.get('name', ''))
        self.path_edit.setText(icon.get('path', ''))

        if len(self.path_edit.text()) > 0:
            filename = f'{os.getcwd()}/icons/{self.path_edit.text()}'
            if os.path.exists(filename):
                pixmap = QPixmap(filename, 'PNG')
                self.preview_img.setPixmap(pixmap)
                self.preview_img.setFixedSize(pixmap.size().grownBy(QMargins(4, 4, 4, 4)))

        design_type = icon.get('design', None)
        if design_type is not None:
            if design_type == 0:
                self.standard_design_radiobutton.setChecked(True)
            elif design_type == 1:
                self.flat_design_radiobutton.setChecked(True)

    def _open_file_clicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Open Image"), "icons",
                                                  self.tr("png-file") + " (*.png)",
                                                  options=QFileDialog.Option.DontUseNativeDialog)

        if filename != '':
            self.path_edit.setText(os.path.relpath(filename, self.base_dir))
            pixmap = QPixmap(filename, 'PNG')
            self.preview_img.setPixmap(pixmap)
            self.preview_img.setFixedSize(pixmap.size().grownBy(QMargins(4, 4, 4, 4)))

    def _save_contents(self, icon):
        if len(self.name_edit.text()) > 0:
            icon['name'] = self.name_edit.text()
        elif 'name' in icon:
            del icon['name']

        if len(self.path_edit.text()) > 0:
            icon['path'] = self.path_edit.text()
        elif 'path' in icon:
            del icon['path']

        if self.button_group.checkedId() in range(2):
            icon['design'] = self.button_group.checkedId()
        elif 'design' in self.connection:
            del icon['design']

