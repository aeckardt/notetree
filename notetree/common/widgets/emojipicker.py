import math

from PyQt6.QtCore import (QSize, QRect, QRectF, QMargins, Qt, QEvent, QPoint, pyqtSignal)
from PyQt6.QtGui import (QPainter, QPainterPath, QColor, QHoverEvent, QFontMetricsF, QMouseEvent,
                         QEnterEvent)
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton)

from notetree.common.utils.errormessage import show_error_msg
from notetree.common.utils.settings import settings

class EmojiPicker(QWidget):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()

    def __init__(self, emojis = [], index = -1, emojis_per_line = 12, parent = None):
        super().__init__(parent)

        self.index = index
        self.highlighted = -1
        self.clicked_index = -1
        self.emojis = emojis
        self.spacing = 0
        self.border_width = 1
        self.emojis_per_row = emojis_per_line

        font = self.font()
        font.setPointSize(16)
        self.setFont(font)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_index(self, index):
        if index != self.index:
            self.index = index
            self.update()

    def selected_emoji(self):
        if self.index == -1:
            return None
        return self.emojis[self.index]

    def setEnabled(self, enabled):
        if enabled == self.isEnabled():
            return
        super().setEnabled(enabled)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, enabled)

    def _emoji_size(self):
        canvas_width = self.width() - 2 * self.border_width
        canvas_height = self.height() - 2 * self.border_width

        emoji_count = len(self.emojis)
        column_count = max(1, min(self.emojis_per_row, emoji_count))
        row_count = math.ceil((emoji_count - 0.01) / column_count)

        width = int((canvas_width - self.spacing * (column_count - 1)) / column_count)
        height = int((canvas_height - self.spacing * (row_count - 1)) / row_count)

        return QSize(width, height)

    def _emoji_rect(self, index):
        column_count = max(1, min(self.emojis_per_row, len(self.emojis)))
        column = index % column_count
        row = index // column_count

        size = self._emoji_size()

        left = self.border_width + (column * (size.width() + self.spacing))
        top = self.border_width + (row * (size.height() + self.spacing))

        return QRect(left, top, size.width(), size.height())

    def _index_of(self, pos):
        for index in range(len(self.emojis)):
            cr = self._emoji_rect(index)
            if cr.contains(pos):
                return index
        return -1

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)

        border_margins = QMargins(self.border_width, self.border_width, self.border_width, self.border_width)

        painter.setPen(QColor('white'))
        rect = self.rect() - border_margins
        painter.fillRect(rect, QColor('white'))

        fm = QFontMetricsF(self.font())

        for index in range(len(self.emojis)):
            emoji = self.emojis[index]
            rect = self._emoji_rect(index)

            bounding_rect = fm.boundingRect(emoji).toRect()
            label_pos = rect.center() - bounding_rect.center() + QPoint(1, 1)

            painter.drawText(label_pos, emoji)

            if index == self.index:
                rect_f = QRectF(rect.adjusted(0, 0, -1, -1))
                path = QPainterPath()
                path.addRect(rect_f)

                painter.setPen(QColor('#7f7f7f'))
                painter.drawPath(path)

            elif index == self.highlighted:
                rect_f = QRectF(rect.adjusted(0, 0, -1, -1))
                path = QPainterPath()
                path.addRect(rect_f)

                painter.setPen(QColor('#cfcfcf'))
                painter.drawPath(path)

        rect_f = QRectF(self.rect().adjusted(0, 0, -1, -1))
        path = QPainterPath()
        path.addRect(rect_f)

        painter.setPen(QColor('#bfbfbf'))
        painter.drawPath(path)

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._index_of(event.position().toPoint())
            if index != -1 and self.index != index:
                self.index = index
                self.clicked_index = index
                self.update()
                self.clicked.emit()
            elif index != -1 and self.clicked_index != index:
                self.clicked_index = index
                self.update()
                self.clicked.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._index_of(event.position().toPoint())
            if index != -1 and self.index != index:
                self.index = index
                self.clicked_index = index
                self.update()
            elif index != -1 and self.clicked_index != index:
                self.clicked_index = index
                self.update()
            self.double_clicked.emit()

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_index = -1
            self.update()

    def enterEvent(self, event: QEnterEvent):
        if self.isEnabled():
            index = self._index_of(event.position().toPoint())
            if self.highlighted != index:
                self.highlighted = index
                self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent):
        if self.highlighted != -1:
            self.highlighted = -1
            self.update()
        super().leaveEvent(event)

    def hover_move_event(self, event: QHoverEvent):
        if self.isEnabled():
            index = self._index_of(event.position().toPoint())
            if self.highlighted != index:
                self.highlighted = index
                self.update()

    def event(self, event):
        if event.type() == QEvent.Type.HoverMove:
            self.hover_move_event(event)
            return True
        return super().event(event)

    def minimumSizeHint(self):
        if len(self.emojis) >= self.emojis_per_row:
            columns = self.emojis_per_row
            rows = math.ceil(len(self.emojis) / columns)
        else:
            columns = len(self.emojis)
            rows = 1

        min_width = 28
        min_height = 28

        return QSize(2 * self.border_width + min_width * columns + self.spacing * (columns - 1),
                     2 * self.border_width + min_height * rows + self.spacing * (rows - 1))

    def sizeHint(self):
        return self.minimumSizeHint()

class EmojiPickerDialog(QDialog):
    def __init__(self, title: str, parent: QWidget = None):
        QDialog.__init__(self, parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Available emojis
        emojis = ['😃', '😄', '😁', '😅', '😂', '😊', '😇', '🙂', '🙃',
                  '😉', '😌', '😍', '🥰', '😘', '😋', '😛', '😜', '🤪', '🤨',
                  '🤔', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔',
                  '😫', '😢', '🥹', '😭', '😳', '🤯', '🥵', '🥶', '😨', '🫣',
                  '🤗', '🤭', '🤫', '😬', '🥱', '😴', '😵', '🤮', '🤒', '🤕',
                  '💩', '👻', '🙏', '👍', '👎', '💪', '👌', '👉', '👇',
                  '🧘', '🙋',
                  '👣', '👀', '🧠', '🙈', '🙉', '🙊', 
                  '🦊', '🐰', '🐇', '🦆', '🦜', '🕊', '🐝', '🦋', '🐞', '🐢',
                  '🐏', '🐑',
                  '🐕', '🦮', '🐈', '🐿',
                  '🌲', '🌳', '🌴', '🌱', '🌿', '🍀', '🌎', '🌍', '🌏',
                  '🌞', '🌤', '🌧', '🌈', '💫', '✨',
                  '🔥', '🌬', '💦',
                #   '🍏', '🍎', '🍐', '🍊', '🍌', '🍓', '🫐', '🍒', '🥥', '🥝',
                #   '🍅', '🥦', '🥬', '🥒', '🫑', '🌽', '🥕', '🧄', '🧅', '🥔',
                #   '🍪', '🌰', '🥜', '🥄', '🍴', '🍽',
                  '🍺', '🧊',
                  '🎼', '🎹', '🎶', '🎵', '🧳',
                  '🚗', '🚘', '🚲',
                  '⛰', '🏕', '⛺️', '🏠', '🏡', '🌅', '🏞', '🌄', '🖼',
                  '🎨', '💶',
                  '🛒', '🛠', '🔨', '🗝', '📅', '📜', '⏱️', '💡', '🧱', '🧩',
                  '📚', '📖', '🔗', '📎', '🖍', '📌', '🎧', '🔍',
                  '🎁', '💬', '🕯', '🎈', '🧬', '🔭',
                  '💗', '💘', '💕', '🧡', '💚', '💙', '💔',
                  '✅', '❌', '🚫', '🟢', '🟡', '🔴', '🔵',
                  '🔁', '🔄', '🆚'
                ]
        self.emoji_picker = EmojiPicker(emojis, -1, 20)
        self.emoji_picker.double_clicked.connect(self.accept)
        layout.addWidget(self.emoji_picker, 1)

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

        self.setWindowTitle(title)

        settings.restore_geometry(self)

    def accept(self):
        if self.emoji_picker.index == -1:
            show_error_msg('Es wurde kein Emoji ausgewählt', self)
            return

        settings.save_geometry(self)
        super().accept()

    def reject(self):
        settings.save_geometry(self)
        super().reject()
