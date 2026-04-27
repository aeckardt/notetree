from PyQt6.QtWidgets import (QWidget, QMessageBox)

def show_error_msg(text: str, parent: QWidget):
    Button = QMessageBox.StandardButton
    msgbox = QMessageBox(QMessageBox.Icon.Critical, "Fehler", text, Button.Ok, parent)
    msgbox.setDefaultButton(Button.Ok)
    msgbox.open()
