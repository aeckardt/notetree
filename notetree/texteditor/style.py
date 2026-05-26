import sys

from PyQt6.QtGui import (QTextListFormat, QColor, QTextBlockFormat, QTextCharFormat, QTextLength,
                         QGuiApplication, QFont)

# -----------------------------------------------
# 1. Modifiable style constants
# -----------------------------------------------

# TextEditor styles
ListStyle = QTextListFormat.Style
TOP_LEVEL_LIST_STYLE = ListStyle.ListDisc.value
LOWER_LEVEL_LIST_STYLE = ListStyle.ListCircle.value
LINK_COLOR = QColor('#1c37e5')
ALT_LINK_COLOR = QColor('#fa6c13') # is currently not used
LIST_PADDING = "  "
LIST_PADDING_LENGTH = len(LIST_PADDING)

# Optional TextEditor styles (remove to deactivate)
DOCUMENT_INDENT_WIDTH = 30
VIEWPORT_MARGIN = 15
BLOCK_LINE_HEIGHT = '125%'
BLOCK_TOP_MARGIN = 0
BLOCK_BOTTOM_MARGIN = 2
HORIZONTAL_RULER_WIDTH = '50%'
HORIZONTAL_RULER_COLOR = QColor('#999')

# -----------------------------------------------
# 2. Initialization methods
# -----------------------------------------------

style_module = sys.modules[__name__]

def init_default_block_format() -> QTextBlockFormat:
    """
    Sets up properties for a QTextBlockFormat that is used each time
    a new block is added to a QTextDocument in TextEditor.
    """
    # Define aliases
    BlockProperty = QTextBlockFormat.Property
    LineHeightType = QTextBlockFormat.LineHeightTypes
    ProportionalHeight = LineHeightType.ProportionalHeight.value
    FixedHeight = LineHeightType.FixedHeight.value

    # Optional styles
    line_height = getattr(style_module, 'BLOCK_LINE_HEIGHT', None)
    top_margin = getattr(style_module, 'BLOCK_TOP_MARGIN', None)
    bottom_margin = getattr(style_module, 'BLOCK_BOTTOM_MARGIN', None)

    # Apply styles to QTextBlockFormat
    block_fmt = QTextBlockFormat()
    if line_height is not None:
        if isinstance(line_height, str) and line_height.endswith('%'):
            block_fmt.setProperty(BlockProperty.LineHeightType, ProportionalHeight)
            block_fmt.setProperty(BlockProperty.LineHeight, float(line_height.rstrip(' %')))
        else:
            block_fmt.setProperty(BlockProperty.LineHeightType, FixedHeight)
            block_fmt.setProperty(BlockProperty.LineHeight, float(line_height))
    if top_margin is not None:
        block_fmt.setProperty(BlockProperty.BlockTopMargin, float(top_margin))
    if bottom_margin is not None:
        block_fmt.setProperty(BlockProperty.BlockBottomMargin, float(bottom_margin))

    return block_fmt

def init_horizontal_ruler_width() -> QTextLength:
    """
    Sets up the width for the horizontal ruler object in QTextDocument.
    """
    LengthType = QTextLength.Type

    # Retrieve optional style from module
    width = getattr(style_module, 'HORIZONTAL_RULER_WIDTH', None)
    if width is None:
        return QTextLength()

    if isinstance(width, str) and width.endswith('%'):
        return QTextLength(LengthType.PercentageLength, float(width.rstrip(' %')))
    else:
        return QTextLength(LengthType.FixedLength, float(width))

def init_default_font_pointsize() -> int:
    # Return default fontsize from application, if available
    if QGuiApplication.instance():
        return QGuiApplication.font().pointSize()
    # Return some pointsize as default
    # It will be used only for test cases, since they cannot use QGuiApplication
    return 13

def init_default_char_format() -> QTextCharFormat:
    char_fmt = QTextCharFormat()
    if not QGuiApplication.instance():
        char_fmt.setFontPointSize(init_default_font_pointsize())
    return char_fmt

# -----------------------------------------------
# 3. Definition of constants that need init.
# -----------------------------------------------

# Default block format for TextEditor
default_block_format = init_default_block_format()
horizontal_ruler_width = init_horizontal_ruler_width()
horizontal_ruler_color = getattr(style_module, 'HORIZONTAL_RULER_COLOR', None)

# Default char format for TextEditor
# Needs to be initialized after QGuiApplication starts running
default_char_format = None
default_font_pointsize = None
