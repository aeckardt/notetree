from enum import IntEnum

from PyQt6.QtCore import (QEvent, QSize, QRect, QRectF, QPoint, Qt, pyqtSignal)
from PyQt6.QtGui import (QImage, QPainter, QPainterPath, QColor, QFontMetrics, QLinearGradient)
from PyQt6.QtWidgets import (QWidget, QGraphicsDropShadowEffect)

SHADOW_BLUR_RADIUS = 15
SHADOW_COLOR = QColor("#8eb7f1")

def to_grayscale(image: QImage, brightness_factor):
    width = image.width()
    height = image.height()

    grayscale_image = QImage(width, height, QImage.Format.Format_ARGB32)
    for y in range(height):
        for x in range(width):
            rgb = image.pixel(x, y) & int("0xffffff", 0)
            alpha = int((image.pixel(x, y) - rgb) / int("0xffffff", 0))
            red = rgb & int("0xff", 0)
            green = int((rgb & int("0x00ff", 0)) / int("0x100", 0))
            blue = int((rgb & int("0x0000ff", 0)) / int("0x10000", 0))
            avg_bright = int((brightness_factor * 255 + red + green + blue) / (3 + brightness_factor))
            grayscale_image.setPixel(x, y, alpha * int("0x1000000", 0) + avg_bright * int("0x010101", 0))

    return grayscale_image

class GradientButton(QWidget):
    class State(IntEnum):
        DISABLED = 1
        INACTIVE = 2
        ACTIVE = 3
        CLICKED = 4
        CHECKED = 5

    class Type(IntEnum):
        IMAGE_BUTTON = 1
        TEXT_BUTTON = 2

    clicked = pyqtSignal()

    # -----------------------------------------------
    # 1. Constructor / Initialization
    # -----------------------------------------------

    def __init__(self, image: QImage | None = None, use_grayscale=True,
                 text: str = '', text_alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
                 focus_widget=False, base_color=QColor('#ebebeb'),
                 checked_color: QColor | None = None, parent: QWidget | None = None):
        super().__init__(parent)

        if image is not None:
            if text != '':
                raise Exception('No implementation available for GradientButton with both image and text')
            self.type = GradientButton.Type.IMAGE_BUTTON
        else:
            self.type = GradientButton.Type.TEXT_BUTTON

        self.checkable = False
        self.checked = False
        self.mouse_pressed = False

        self.shadow = QGraphicsDropShadowEffect(self)

        self.colors = [0] * 5
        self.checked_colors = [0] * 5
        self.gradient = QLinearGradient()
        self.label_rect = QRect()

        self.key_state = 0
        self.offset = 0

        self.alignment = text_alignment

        if self.type == GradientButton.Type.IMAGE_BUTTON:
            if use_grayscale:
                self.image = to_grayscale(image, 0.5)
            else:
                self.image = image
            self.disabled_image = to_grayscale(image, 5)
        elif self.type == GradientButton.Type.TEXT_BUTTON:
            if text != '':
                self.set_text(text)
            else:
                self.text = ''

        self.state = -1

        if focus_widget:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.shadow_enabled = True
        else:
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.shadow_enabled = False
        self.set_base_color(base_color, checked_color)

        self._set_state(GradientButton.State.INACTIVE)

        self.shadow.setBlurRadius(SHADOW_BLUR_RADIUS)
        self.shadow.setOffset(1, 0)
        self.shadow.setColor(SHADOW_COLOR)
        self.setGraphicsEffect(self.shadow)

    # -----------------------------------------------
    # 2. Property management
    # -----------------------------------------------

    def set_text(self, text):
        fm = QFontMetrics(self.font())
        self.label_rect = fm.boundingRect(text)
        self.text = text
        self.text_pos = self._calc_text_pos()

    def set_image(self, image: QImage, use_grayscale=True):
        if self.type != GradientButton.Type.IMAGE_BUTTON:
            raise RuntimeError("set_image() is only available for image buttons")

        if use_grayscale:
            self.image = to_grayscale(image, 0.5)
        else:
            self.image = image

        self.disabled_image = to_grayscale(image, 5)
        self.image_pos = self._calc_image_pos()
        self.update()

    def setFont(self, font):
        fm = QFontMetrics(self.font())
        self.label_rect = fm.boundingRect(self.text)
        super().setFont(font)

    def set_base_color(self, color, checked_color=None):
        self.colors = [self._adjust_color(color, i * 16) for i in range(5)]
        if checked_color:
            self.checked_colors = [self._adjust_color(checked_color, i * 8) for i in range(5)]
        else:
            self.checked_colors = self.colors

    def _adjust_color(self, color, adjustment):
        return QColor(min(255, color.red() + adjustment),
                      min(255, color.green() + adjustment),
                      min(255, color.blue() + adjustment))

    def set_checkable(self, checkable):
        if checkable == self.checkable:
            return
        self.checkable = checkable
        self._update_state()

    def is_checked(self):
        return self.checkable and self.checked

    def set_checked(self, checked):
        if self.checked != checked:
            self.checked = checked
            self._update_state()

    def set_shadow_enabled(self, enabled):
        if self.shadow_enabled != enabled:
            self.shadow_enabled = enabled
            self._update_shadow_state()

    # -----------------------------------------------
    # 3. State management
    # -----------------------------------------------

    def _set_state(self, new_state):
        if new_state == self.state:
            return

        self.state = new_state
        if new_state == GradientButton.State.DISABLED:
            self.gradient.setColorAt(0,    QColor("#d7d7d7"))
            self.gradient.setColorAt(0.15, QColor("#dfdfdf"))
            self.gradient.setColorAt(0.5,  QColor("#e7e7e7"))
            self.gradient.setColorAt(0.85, QColor("#efefef"))
            self.gradient.setColorAt(1,    QColor("#f3f3f3"))
            self.offset = 0
            self.text_color = QColor("#555555")
        elif new_state == GradientButton.State.CLICKED:
            self.gradient.setColorAt(0,    self.colors[0])
            self.gradient.setColorAt(0.15, self.colors[1])
            self.gradient.setColorAt(0.5,  self.colors[2])
            self.gradient.setColorAt(0.85, self.colors[3])
            self.gradient.setColorAt(1,    self.colors[4])
            self.offset = 1
            self.text_color = QColor("#111111")
        elif new_state == GradientButton.State.CHECKED:
            self.gradient.setColorAt(0,    self.checked_colors[0])
            self.gradient.setColorAt(0.15, self.checked_colors[1])
            self.gradient.setColorAt(0.5,  self.checked_colors[2])
            self.gradient.setColorAt(0.85, self.checked_colors[3])
            self.gradient.setColorAt(1,    self.checked_colors[4])
            self.offset = 1
            self.text_color = QColor("#111111")
        elif new_state in [GradientButton.State.INACTIVE, GradientButton.State.ACTIVE]:
            self.gradient.setColorAt(0,    self.colors[4])
            self.gradient.setColorAt(0.15, self.colors[3])
            self.gradient.setColorAt(0.5,  self.colors[2])
            self.gradient.setColorAt(0.85, self.colors[1])
            self.gradient.setColorAt(1,    self.colors[0])
            self.offset = 0
            self.text_color = QColor("#111111")

        if self.type == GradientButton.Type.IMAGE_BUTTON:
            self.image_pos = self._calc_image_pos()
        else:
            self.text_pos = self._calc_text_pos()

        self._update_shadow_state()

    def _update_shadow_state(self):
        if self.state in [GradientButton.State.INACTIVE, GradientButton.State.DISABLED]:
            self.shadow.setEnabled(False)
        else:
            self.shadow.setEnabled(self.shadow_enabled)

    def _update_state(self):
        # Determine the current state of the button based on its context.
        old_state = self.state

        if not self.isEnabled():
            self._set_state(GradientButton.State.DISABLED)
        elif self.mouse_pressed or self.key_state != 0:
            # Set clicked state if mouse button or Space is pressed
            self._set_state(GradientButton.State.CLICKED)
        elif self.checkable and self.checked:
            self._set_state(GradientButton.State.CHECKED)
        elif self.hasFocus():
            self._set_state(GradientButton.State.ACTIVE)
        else:
            self._set_state(GradientButton.State.INACTIVE)

        if old_state != self.state:
            self.update()

    # -----------------------------------------------
    # 4. Rendering functions
    # -----------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)

        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.fillRect(rect, self.gradient)

        path = QPainterPath()
        path.addRect(QRectF(rect))

        painter.setPen(QColor("#dfdfdf"))
        painter.drawPath(path)

        if self.type == GradientButton.Type.IMAGE_BUTTON:
            if self.state != GradientButton.State.DISABLED:
                painter.drawImage(self.image_pos, self.image)
            elif self.disabled_image is not None:
                painter.drawImage(self.image_pos, self.disabled_image)
        elif self.text != '':
            painter.setFont(self.font())
            painter.setPen(self.text_color)
            painter.drawText(self.text_pos.x(), self.text_pos.y() + self.font().pointSize(), self.text)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.gradient.setStart(0, 0)
        self.gradient.setFinalStop(0, self.height())

        if self.type == GradientButton.Type.IMAGE_BUTTON:
            self.image_pos = self._calc_image_pos()
        else:
            self.text_pos = self._calc_text_pos()

    def minimumSizeHint(self):
        if self.type == GradientButton.Type.IMAGE_BUTTON:
            return self.image.rect().size() + QSize(6, 6)
        elif self.text != '':
            return self.label_rect.size() + QSize(12, 6)
        else:
            return QSize(1, 1)

    def sizeHint(self):
        if self.type == GradientButton.Type.IMAGE_BUTTON:
            return self.image.rect().size() + QSize(12, 10)
        elif self.text != '':
            return self.label_rect.size() + QSize(12, 6)
        else:
            return QSize(1, 1)

    def _calc_image_pos(self):
        offset = QPoint(self.offset, self.offset)
        return self.rect().center() - self.image.rect().center() + offset

    def _calc_text_pos(self):
        offset = QPoint(self.offset, self.offset)
        top_left = self.rect().center() - self.label_rect.center() - QPoint(0, self.font().pointSize() - 0)
        if self.alignment == Qt.AlignmentFlag.AlignCenter:
            return top_left + offset
        elif self.alignment == Qt.AlignmentFlag.AlignLeft:
            return QPoint(0, top_left.y()) + offset
        else:
            raise Exception('Alignment not available for GradientButton')

    # -----------------------------------------------
    # 5. Mouse/Key input handlers
    # -----------------------------------------------

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = True
            self._update_state()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = False
            if self.rect().contains(event.pos()):
                if self.checkable:
                    self.checked = not self.checked
                self.clicked.emit()
            self._update_state()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() in [Qt.Key.Key_Space]:
            self.key_state |= event.key()
            self.clicked.emit()
            self._update_state()
        elif event.key() == Qt.Key.Key_Tab:
            self.key_state = 0
            self._update_state()
        
    def keyReleaseEvent(self, event):
        super().keyPressEvent(event)
        if event.key() in [Qt.Key.Key_Space]:
            self.key_state &= ~event.key()
            self._update_state()
            
    # -----------------------------------------------
    # 6. Other event handlers
    # -----------------------------------------------

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange:
            self._update_state()
        super().changeEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._update_state()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._update_state()

    def focusNextPrevChild(self, next):
        return False

