from PyQt6.QtCore import (QRectF, Qt)
from PyQt6.QtGui import (QPainter, QPainterPath, QColor, QPen)
from PyQt6.QtWidgets import (QWidget)

class ToolBarSeparator(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setFixedWidth(5)

    def paintEvent(self, event):
        painter = QPainter(self)

        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.fillRect(rect, QColor("#efefef"))

        pen = QPen(Qt.PenStyle.DotLine)
        pen.setColor(QColor('#d7d7d7'))
        painter.setPen(pen)

        _rect = rect.adjusted(0, 0, -4, 0)
        path = QPainterPath()
        path.addRect(QRectF(_rect))
        painter.drawPath(path)

        _rect = rect.adjusted(4, 0, 0, 0)
        path = QPainterPath()
        path.addRect(QRectF(_rect))
        painter.drawPath(path)
