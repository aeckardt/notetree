from PyQt6.QtWidgets import (QDialog)

from notetree.common.widgets.tablebuttonwidget import TableButtonWidget
from notetree.library.icons.datacontainer import icons
from notetree.library.icons.editor import IconEditorDialog
from notetree.library.icons.model import IconModel

class IconTableWidget(TableButtonWidget):
    def __init__(self, model: IconModel):
        super().__init__('Icons', model, True)
        self.model = model

    def add_row(self):
        new_icon = {}
        editor = IconEditorDialog("Icon hinzufügen...", new_icon)
        if editor.exec() == QDialog.DialogCode.Accepted:
            icons.append(new_icon)

    def remove_row(self):
        icon = self.model.item_at(self.selected_row)
        icons.remove(icon)

    def edit_row(self):
        icon = self.model.item_at(self.selected_row)
        editor = IconEditorDialog("Icon bearbeiten...", icon)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.update_row(self.selected_row)
