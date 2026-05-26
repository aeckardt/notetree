import math

import os
import sys
import webbrowser
import subprocess
import platform
import pathlib
from dataclasses import dataclass

from PyQt6.QtCore import (QSize, Qt, pyqtSlot, pyqtSignal, QMimeData)
from PyQt6.QtGui import (QTextCharFormat, QTextListFormat, QFont, QTextCursor, QFontDatabase,
                         QColor, QImage, QKeyEvent, QCursor, QTextCursor, QTextFormat, QTextDocument, 
                         QKeySequence, QGuiApplication, QTextDocumentFragment, QAction, QTextBlock)
from PyQt6.QtWidgets import (QWidget, QTextEdit, QVBoxLayout, QToolBar, QComboBox, QDialog,
                             QFileDialog, QMenu)
from PyQt6.QtPrintSupport import (QPrinter)

from notetree.common.widgets.emojipicker import EmojiPickerDialog
from notetree.common.widgets.gradientbutton import GradientButton
from notetree.texteditor.html.exporter import HtmlExporter
from notetree.texteditor.html.importer import HtmlImporter
from notetree.texteditor.markdown.exporter import MarkdownExporter
from notetree.texteditor.style import *
from notetree.texteditor.widgets.linkeditor import LinkEditorDialog
from notetree.texteditor.widgets.toolbarseparator import ToolBarSeparator

@dataclass
class Hyperlink:
    cursor: QTextCursor
    position: int
    length: int
    text: str
    href: str

class TextEditor(QTextEdit):
    # -----------------------------------------------
    # 1. Constructor / Initialization
    # -----------------------------------------------

    font_changed = pyqtSignal(QFont)
    block_format_changed = pyqtSignal()

    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)

        # Initialize default char format (QGuiApplication needs to be initialized)
        global default_char_format, default_font_pointsize
        if not default_char_format:
            default_char_format = init_default_char_format()
            default_font_pointsize = init_default_font_pointsize()

        # Connect signals
        self.currentCharFormatChanged.connect(self._on_current_charformat_changed)
        self.cursorPositionChanged.connect(self._on_cursor_position_changed)
        self.selectionChanged.connect(self._on_selection_changed)

        # Setup actions and menus
        self._setup_actions()
        self._setup_context_menu()

        # Set viewport margin, if set
        viewport_margin = getattr(style_module, 'VIEWPORT_MARGIN', None)
        if viewport_margin is not None:
            self.setViewportMargins(viewport_margin, viewport_margin, viewport_margin, viewport_margin)
            self.setStyleSheet("QTextEdit { background: white; }")

        # Set working directory to be able to open file links
        self.root_directory = None

        # Initialize properties
        self._anchor = None
        self._ctrl_pressed = False

        # Initialize X coordinate of the cursor for navigating with Up/Down keys
        self._cursor_x = -1
        self._keep_cursor_x = False

    def _setup_actions(self):
        self.undo_action = QAction(self.tr("Undo"), self)
        self.undo_action.setEnabled(False)
        self.undo_action.setShortcut(QKeySequence('Ctrl+Z'))
        self.undoAvailable.connect(self.undo_action.setEnabled)
        self.undo_action.triggered.connect(self.undo)

        self.redo_action = QAction(self.tr("Redo"), self)
        self.redo_action.setEnabled(False)
        self.redo_action.setShortcut(QKeySequence('Ctrl+Shift+Z'))
        self.redoAvailable.connect(self.redo_action.setEnabled)
        self.redo_action.triggered.connect(self.redo)

        self.cut_action = QAction(self.tr("Cut"), self)
        self.cut_action.setEnabled(False)
        self.cut_action.triggered.connect(self.cut)

        self.copy_action = QAction(self.tr("Copy"), self)
        self.copy_action.setEnabled(False)
        self.copy_action.triggered.connect(self.copy)

        self.paste_action = QAction(self.tr("Paste"), self)
        self.paste_action.setEnabled(self.canPaste())
        QGuiApplication.clipboard().dataChanged.connect(self._clipboard_update)
        self.paste_action.triggered.connect(self.paste)

        self.delete_action = QAction(self.tr("Delete"), self)
        self.delete_action.setEnabled(False)
        self.delete_action.triggered.connect(self.textCursor().removeSelectedText)

        self.text_bold_action = QAction(self.tr("Bold"), self)
        self.text_bold_action.setCheckable(True)
        self.text_bold_action.setShortcut(QKeySequence('Ctrl+B'))
        self.text_bold_action.triggered.connect(self.toggle_bold)
        self.addAction(self.text_bold_action)

        self.text_italic_action = QAction(self.tr("Italic"), self)
        self.text_italic_action.setCheckable(True)
        self.text_italic_action.setShortcut(QKeySequence('Ctrl+I'))
        self.text_italic_action.triggered.connect(self.toggle_italic)
        self.addAction(self.text_italic_action)

        self.text_underline_action = QAction(self.tr("Underline"), self)
        self.text_underline_action.setCheckable(True)
        self.text_underline_action.setShortcut(QKeySequence('Ctrl+U'))
        self.text_underline_action.triggered.connect(self.toggle_underline)
        self.addAction(self.text_underline_action)

        self.textsize_plus_action = QAction(self.tr("Increase font size"), self)
        self.textsize_plus_action.setShortcut(QKeySequence('Ctrl++'))
        self.textsize_plus_action.triggered.connect(self._textsize_plus)
        self.addAction(self.textsize_plus_action)

        self.textsize_minus_action = QAction(self.tr("Decrease font size"), self)
        self.textsize_minus_action.setShortcut(QKeySequence('Ctrl+-'))
        self.textsize_minus_action.triggered.connect(self._textsize_minus)
        self.addAction(self.textsize_minus_action)

        self.less_indent_action = QAction(self.tr("Decrease list indent"), self)
        self.less_indent_action.setShortcut(QKeySequence('Shift+Tab'))
        self.less_indent_action.triggered.connect(self.unindent_selection)

        self.more_indent_action = QAction(self.tr("Increase list indent"), self)
        self.more_indent_action.setShortcut(QKeySequence('Tab'))
        self.more_indent_action.triggered.connect(self.indent_selection)

        self._link_for_editing: Hyperlink = None
        self.edit_link_action = QAction(self.tr("Edit link"), self)
        self.edit_link_action.setEnabled(False)
        self.edit_link_action.triggered.connect(self.edit_hyperlink)

        self.insert_emoji_action = QAction(self.tr("Insert emoji..."), self)
        self.insert_emoji_action.setShortcut(QKeySequence('Ctrl+E'))
        self.insert_emoji_action.triggered.connect(self.insert_emoji)
        self.addAction(self.insert_emoji_action)

    def _setup_context_menu(self):
        self.context_menu = QMenu()

        self.context_menu.addAction(self.edit_link_action)
        self.menu_separator_action = QAction(self)
        self.menu_separator_action.setSeparator(True)
        self.context_menu.addAction(self.menu_separator_action)

        self.context_menu.addAction(self.undo_action)
        self.context_menu.addAction(self.redo_action)
        self.context_menu.addSeparator()

        self.context_menu.addAction(self.cut_action)
        self.context_menu.addAction(self.copy_action)
        self.context_menu.addAction(self.paste_action)
        self.context_menu.addAction(self.delete_action)

    # -----------------------------------------------
    # 2. Public methods - Export/Import document
    # -----------------------------------------------

    def set_document(self, document: QTextDocument):
        # Change tab indent width (which me thinks, looks better than such a wide tab)
        indent_width = getattr(style_module, 'DOCUMENT_INDENT_WIDTH', None)
        if indent_width is not None:
            document.setIndentWidth(indent_width)

        # Assign the imported document to the editor
        QTextEdit.setDocument(self, document)

        # Update undo, redo actions (the undoAvailable signal might not have been emitted)
        self.undo_action.setEnabled(document.isUndoAvailable())
        self.redo_action.setEnabled(document.isRedoAvailable())

        # Move cursor to the start
        self.moveCursor(QTextCursor.MoveOperation.Start)
        self.ensureCursorVisible()

    # -----------------------------------------------
    # 3. Private methods - QTextEdit slots
    # -----------------------------------------------

    @pyqtSlot(QTextCharFormat)
    def _on_current_charformat_changed(self, char_fmt):
        self.font_changed.emit(char_fmt.font())

        self.text_bold_action.setChecked(is_markdown_strong(char_fmt))
        self.text_italic_action.setChecked(char_fmt.font().italic())
        self.text_underline_action.setChecked(char_fmt.font().underline())

    @pyqtSlot()
    def _on_cursor_position_changed(self):
        self.block_format_changed.emit()

        cursor = self.textCursor()

        if not self._keep_cursor_x:
            self._set_cursor_x(cursor)
        else:
            self._keep_cursor_x = False

        format = cursor.charFormat()
        if format.isAnchor() and not cursor.hasSelection():
            anchor = self._get_link_under_cursor(cursor)
            if anchor is None:
                # Change current char format at the beginning or end of a link
                # Thus the user can continue to write normal text, i.e. not with an anchor 
                char_fmt = QTextCharFormat()
                char_fmt.setAnchor(False)
                char_fmt.setAnchorHref(None)
                char_fmt.setForeground(QColor('black'))
                cursor.mergeCharFormat(char_fmt)
                self.mergeCurrentCharFormat(char_fmt)

    @pyqtSlot()
    def _on_selection_changed(self):
        cursor = self.textCursor()
        self.cut_action.setEnabled(cursor.hasSelection())
        self.copy_action.setEnabled(cursor.hasSelection())
        self.delete_action.setEnabled(cursor.hasSelection())

    # -----------------------------------------------
    # 4. Private methods - CharFormat manipulation
    # -----------------------------------------------

    @pyqtSlot()
    def toggle_bold(self):
        cursor = self.textCursor()
        base_weight = default_font_weight(cursor.block())

        # Watch out here:
        # The checked state has already been changed after triggering the action
        new_font_weight = (
            STRONG_FONT_WEIGHT
            if self.text_bold_action.isChecked()
            else base_weight
        )

        fmt = QTextCharFormat()
        fmt.setFontWeight(new_font_weight)
        self._merge_format_on_selection(fmt)

    @pyqtSlot()
    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.text_italic_action.isChecked())
        self._merge_format_on_selection(fmt)

    @pyqtSlot()
    def toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.text_underline_action.isChecked())
        self._merge_format_on_selection(fmt)

    @pyqtSlot(str)
    def change_text_size(self, sel_text):
        heading_lvl = self.textCursor().blockFormat().headingLevel()
        if heading_lvl > 0:
            return

        pointsize = float(sel_text)
        if pointsize > 0:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(pointsize)
            self._merge_format_on_selection(fmt)

    def _textsize_plus(self):
        heading_lvl = self.textCursor().blockFormat().headingLevel()
        if heading_lvl > 0:
            return

        cursor = self.textCursor()
        pointsize = cursor.charFormat().font().pointSize()

        if pointsize < 72:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(pointsize + 1)
            self._merge_format_on_selection(fmt)

    def _textsize_minus(self):
        heading_lvl = self.textCursor().blockFormat().headingLevel()
        if heading_lvl > 0:
            return

        cursor = self.textCursor()
        pointsize = cursor.charFormat().font().pointSize()

        if pointsize > 4:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(pointsize - 1)
            self._merge_format_on_selection(fmt)

    def _merge_format_on_selection(self, format, selectword=False):
        cursor = self.textCursor()

        # Begin edit block here
        # Thus, there won't be two undo actions after this function
        cursor.beginEditBlock()

        # It could make sense to select the word (or the line) under the cursor
        # if nothing else is selected while clicking bold, italic, etc.
        if not cursor.hasSelection() and selectword:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)

        # Merge char format (these lines are copied from the Qt textedit demo)
        cursor.mergeCharFormat(format)
        self.mergeCurrentCharFormat(format)

        # End edit block
        cursor.endEditBlock()

    def _apply_heading_char_format(self, block: QTextBlock, heading_level: int):
        updates = []

        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()

            if fragment.isValid():
                char_fmt = QTextCharFormat(fragment.charFormat())
                is_strong = is_markdown_strong(char_fmt)

                # Set / remove heading-specific visual formatting.
                if heading_level > 0:
                    char_fmt.setFontWeight(STRONG_FONT_WEIGHT if is_strong else HEADING_FONT_WEIGHT)
                    char_fmt.setProperty(QTextCharFormat.Property.FontSizeAdjustment, 4 - heading_level)
                else:
                    char_fmt.setFontWeight(STRONG_FONT_WEIGHT if is_strong else NORMAL_FONT_WEIGHT)
                    char_fmt.clearProperty(QTextCharFormat.Property.FontSizeAdjustment)

                updates.append((
                    fragment.position(),
                    fragment.length(),
                    char_fmt
                ))

            it += 1

        local_cursor = QTextCursor(self.document())

        for position, length, char_fmt in updates:
            local_cursor.setPosition(position)
            local_cursor.setPosition(
                position + length,
                QTextCursor.MoveMode.KeepAnchor,
            )
            local_cursor.setCharFormat(char_fmt)

    def _clear_heading_char_format(self, block: QTextBlock):
        self._apply_heading_char_format(block, 0)

    # -----------------------------------------------
    # 5. Private methods - Text insertion
    # -----------------------------------------------

    @pyqtSlot()
    def insert_hyperlink(self):
        cursor = self.textCursor()
        anchor = self._get_link_under_cursor(cursor)
        if anchor is not None:
            # Edit link under cursor, if available
            self.edit_link_action.setData(anchor)
            self.edit_hyperlink()
            return

        editor = LinkEditorDialog(self.tr("Insert link"))
        if editor.exec() == QDialog.DialogCode.Accepted:
            # Add hyperlink with specific char format
            fmt = cursor.charFormat()
            fmt.setAnchor(True)
            fmt.setAnchorHref(editor.link_url_edit.text())
            fmt.setForeground(LINK_COLOR)
            cursor.insertText(editor.caption_edit.text(), fmt)

            # Normalize char format after inserting the link
            fmt = QTextCharFormat()
            fmt.setAnchor(False)
            fmt.setAnchorHref(None)
            fmt.setForeground(QColor('black'))
            cursor.mergeCharFormat(fmt)
            self.mergeCurrentCharFormat(fmt)

    def edit_hyperlink(self):
        editor = LinkEditorDialog(self.tr("Edit link"))

        anchor: Hyperlink = self.edit_link_action.data()
        editor.link_url_edit.setText(anchor.href)
        editor.caption_edit.setText(anchor.text)
        editor.caption_edit.selectAll()

        if editor.exec() == QDialog.DialogCode.Accepted:
            cursor = anchor.cursor
            fmt = cursor.charFormat()
            fmt.setAnchor(True)
            fmt.setAnchorHref(editor.link_url_edit.text())
            fmt.setForeground(LINK_COLOR)

            cursor.setPosition(anchor.position)
            cursor.setPosition(anchor.position + anchor.length, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(editor.caption_edit.text(), fmt)

            fmt = QTextCharFormat()
            fmt.setAnchor(False)
            fmt.setAnchorHref(None)
            fmt.setForeground(QColor('black'))
            cursor.mergeCharFormat(fmt)

    @pyqtSlot()
    def insert_emoji(self):
        editor = EmojiPickerDialog(self.tr("Insert emoji"))
        if editor.exec() == QDialog.DialogCode.Accepted:
            emoji = editor.emoji_picker.selected_emoji()
            self.textCursor().insertText(emoji)

    # -----------------------------------------------
    # 6. Private methods - BlockFormat manipulation
    # -----------------------------------------------

    def indent_selection(self):
        self._adjust_list_indentation(1)

    def unindent_selection(self):
        self._adjust_list_indentation(-1)

    def _adjust_list_indentation(self, delta: int):
        """
        Indent/Unindent affects selected list items.
        Non-list paragraphs inside the selection are ignored.
        If no selected block is a list item, the action does nothing or is disabled.
        """
        cursor = self.textCursor()
        blocks = self._selected_blocks(cursor)

        list_blocks = [
            block for block in blocks
            if block.isValid() and block.textList() is not None
        ]

        if not list_blocks:
            return

        cursor.beginEditBlock()
        for block in list_blocks:
            self._adjust_list_block_indentation(block, delta)
        cursor.endEditBlock()

        self.block_format_changed.emit()

    def _adjust_list_block_indentation(self, block: QTextBlock, delta: int):
        block_fmt = block.blockFormat()
        current_indent = block_fmt.indent()
        new_indent = max(0, current_indent + delta)

        if new_indent == current_indent:
            return

        block_fmt.setIndent(new_indent)

        block_cursor = QTextCursor(block)
        block_cursor.setBlockFormat(block_fmt)

        if new_indent > 0:
            self._set_list_style(block_cursor, LOWER_LEVEL_LIST_STYLE)
        else:
            self._set_list_style(block_cursor, TOP_LEVEL_LIST_STYLE)

    def set_heading_level(self, level: int):
        cursor = self.textCursor()

        current_lvl = cursor.blockFormat().headingLevel()
        if level == current_lvl:
            # Do nothing
            return

        cursor.beginEditBlock()

        block_fmt = cursor.blockFormat()
        list = cursor.currentList()
        if list:
            # Remove list
            block_fmt.setObjectIndex(-1)

            # Remove the two extra indent spaces
            self._remove_list_padding(cursor.block())

        # Set heading level for block
        block_fmt.setHeadingLevel(level)
        cursor.setBlockFormat(block_fmt)

        # Apply charformat modification
        self._apply_heading_char_format(cursor.block(), level)

        cursor.endEditBlock()

        self.block_format_changed.emit()

    @pyqtSlot()
    def remove_block_style(self):
        cursor = self.textCursor()
        blocks = self._selected_blocks(cursor)

        cursor.beginEditBlock()

        for block in blocks:
            self._remove_block_style_from_block(block)

        cursor.endEditBlock()
        self.block_format_changed.emit()

    def _remove_block_style_from_block(self, block: QTextBlock):
        block_cursor = QTextCursor(block)
        block_fmt = block.blockFormat()
        text_list = block.textList()

        if text_list:
            text_list.remove(block)
            block_fmt.setObjectIndex(-1)
            block_fmt.setIndent(0)
            block_fmt.clearProperty(QTextFormat.Property.ListStyle)

            self._remove_list_padding(block)

        if block_fmt.headingLevel() > 0:
            block_fmt.setHeadingLevel(0)
            self._apply_heading_char_format(block, 0)

        # Reset paragraph-level formatting that should not survive
        block_fmt.setIndent(0)
        block_cursor.setBlockFormat(block_fmt)

    @pyqtSlot()
    def toggle_list(self):
        cursor = self.textCursor()

        cursor.beginEditBlock()

        block = cursor.block()
        block_fmt = block.blockFormat()

        if block_fmt.headingLevel() > 0:
            # Remove heading format
            block_fmt.setHeadingLevel(0)

            # Remove char format used for headings
            self._apply_heading_char_format(block, 0)

        list = cursor.currentList()
        if not list:
            # Setup new list
            list_fmt = QTextListFormat()
            list_fmt.setIndent(1)
            if block_fmt.indent() == 0:
                style = TOP_LEVEL_LIST_STYLE
            else:
                style = LOWER_LEVEL_LIST_STYLE
            list_fmt.setProperty(QTextFormat.Property.ListStyle, style)
            list = cursor.createList(list_fmt)

            block_fmt.setObjectIndex(list.objectIndex())

            # Indent two extra spaces to make it look more balanced
            self._insert_list_padding(cursor.block())

        else:
            # Remove list at current block
            block = cursor.block()
            list.remove(block)

            block_fmt.setObjectIndex(-1)

            # Remove the two extra indent spaces
            self._remove_list_padding(block)

        cursor.setBlockFormat(block_fmt)
        cursor.endEditBlock()

        self.block_format_changed.emit()

    def make_horizontal_ruler(self):
        cursor = self.textCursor()
        block = cursor.block()

        cursor.beginEditBlock()

        block_fmt = cursor.blockFormat()

        if block_fmt.headingLevel() > 0:
            # Remove heading format
            block_fmt.setHeadingLevel(0)

        list = cursor.currentList()
        if list:
            # Remove list property at current block
            block = cursor.block()
            list.remove(block)

            block_fmt.setObjectIndex(-1)

        # Set horizontal ruler property
        block_fmt.setProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth, horizontal_ruler_width)
        if horizontal_ruler_color is not None:
            block_fmt.setProperty(QTextFormat.Property.BackgroundBrush, horizontal_ruler_color)

        # Remove line
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()

        # Update block format
        cursor.setBlockFormat(block_fmt)

        # Add new line
        cursor.insertBlock(default_block_format, default_char_format)

        cursor.endEditBlock()

    def _selected_blocks(self, cursor: QTextCursor) -> list[QTextBlock]:
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        if start == end:
            return [cursor.block()]

        document = self.document()

        first = document.findBlock(start)
        last = document.findBlock(end)

        # If the selection ends exactly at the beginning of a block, that block
        # is not part of the user's visible selection.
        if end == last.position() and last != first:
            last = last.previous()

        blocks = []
        block = first
        while block.isValid():
            blocks.append(block)
            if block == last:
                break
            block = block.next()

        return blocks

    def _insert_list_padding(self, block: QTextBlock):
        # Insert two spaces to list item before text
        if not block.text().startswith(LIST_PADDING):
            local_cursor = QTextCursor(block)
            local_cursor.setPosition(local_cursor.block().position())
            local_cursor.insertText(LIST_PADDING)

    def _remove_list_padding(self, block: QTextBlock):
        # Check if block starts with padding
        if not block.text().startswith(LIST_PADDING):
            return

        # Remove padding
        local_cursor = QTextCursor(block)
        local_cursor.setPosition(block.position())
        local_cursor.setPosition(block.position() + LIST_PADDING_LENGTH,
                                 QTextCursor.MoveMode.KeepAnchor)
        local_cursor.removeSelectedText()

    def _set_list_style(self, cursor: QTextCursor, style):
        # Check if styles are different
        block_fmt = cursor.blockFormat()
        old_style = block_fmt.property(QTextFormat.Property.ListStyle)
        if style == old_style:
            return

        # Change list style
        block_fmt.setProperty(QTextFormat.Property.ListStyle, style)
        cursor.setBlockFormat(block_fmt)

    # -----------------------------------------------
    # 7. Static/Utility Methods
    # -----------------------------------------------

    @staticmethod
    def _get_default_fontsize():
        font = QGuiApplication.font()
        return font.pointSize()

    @staticmethod
    def _system_open_file(dir: pathlib.Path | None, filename: str):
        if dir is not None:
            # Temporarily change working directory
            prev_dir = os.getcwd()
            os.chdir(dir)

        # MacOS
        if platform.system() == 'Darwin':
            subprocess.call(('open', filename))

        # Windows
        elif platform.system() == 'Windows':
            os.startfile(filename)

        # Linux variants
        else:
            try:
                subprocess.call(('xdg-open', filename))
            except:
                print(f'Error opening file "{filename}".', file=sys.stderr)

        if dir is not None:
            # Change working directory back to before
            os.chdir(prev_dir)

    @staticmethod
    def _get_link_under_cursor(cursor: QTextCursor):
        char_fmt = cursor.charFormat()
        if not char_fmt.isAnchor():
            return None

        cur_pos = cursor.position()

        contains_link = False
        block = cursor.block()
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.contains(cur_pos):
                contains_link = True
                break
            it += 1

        if not contains_link:
            return None

        if not fragment.charFormat().isAnchor():
            return None

        first_pos = fragment.position()
        last_pos = fragment.position() + fragment.length()
        text = fragment.text()

        return Hyperlink(cursor, first_pos, last_pos - first_pos, text, char_fmt.anchorHref())

    def export_as_pdf(self):
        # Create new document with different text size
        # Otherwise it will be huge !
        size_factor = 0.80

        doc = QTextDocument()
        doc.setIndentWidth(math.floor(self.document().indentWidth() * size_factor))

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        current_list = None
        pdf_char_fmt = QTextCharFormat()
        point_size = max(4, math.floor(self._get_default_fontsize() * size_factor))
        pdf_char_fmt.setFontPointSize(point_size)

        # Iterate through document to copy text with smaller font size
        block = self.document().firstBlock()
        while block.isValid():
            block_fmt = block.blockFormat()
            text_list = block.textList()

            cursor.setCharFormat(pdf_char_fmt)
            cursor.insertBlock(block_fmt)

            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()

                char_fmt = fragment.charFormat()
                char_fmt.clearProperty(QTextCharFormat.Property.FontSizeAdjustment)

                # Determine font pointsize from block and charformat
                match block_fmt.headingLevel():
                    case 0:
                        point_size = max(4, math.floor(char_fmt.font().pointSize() * size_factor))
                    case 1:
                        point_size = math.floor(26 * size_factor)
                    case 2:
                        point_size = math.floor(20 * size_factor)
                    case 3:
                        point_size = math.floor(16 * size_factor)
                    case 4:
                        point_size = math.floor(13 * size_factor)
                char_fmt.setFontPointSize(point_size)

                cursor.insertText(fragment.text(), char_fmt)

                it += 1

            if text_list:
                if not current_list:
                    current_list = cursor.createList(QTextListFormat.Style.ListDisc)
                current_list.add(cursor.block())
            else:
                current_list = None

            block = block.next()

        cursor.endEditBlock()

        # Open file dialog
        file_dialog = QFileDialog(self, self.tr("Export as PDF"))
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setMimeTypeFilters(["application/pdf"])
        file_dialog.setDefaultSuffix("pdf")
        if file_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if len(file_dialog.selectedFiles()) == 0:
            return

        pdf_filename = file_dialog.selectedFiles()[0]
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_filename)

        # Save size adjusted document to selected file
        doc.print(printer)

    # -----------------------------------------------
    # 8. Event Handlers
    # -----------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        # Overrides for standard keys
        if event.key() == Qt.Key.Key_Tab:
            self.indent_selection()
            return

        elif event.key() == Qt.Key.Key_Backtab:
            self.unindent_selection()
            return

        elif event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.copy()
            return

        elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.paste()
            return

        elif event.key() == Qt.Key.Key_X and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.cut()
            return

        elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            block_fmt = cursor.blockFormat()
            if block_fmt.objectIndex() != -1:
                cursor.insertBlock(block_fmt)
                cursor.insertText(LIST_PADDING)
            else:
                cursor.insertBlock(default_block_format, default_char_format)
            cursor.endEditBlock()
            self.ensureCursorVisible()
            return

        elif event.key() == Qt.Key.Key_Backspace:
            cursor = self.textCursor()
            list = cursor.currentList()
            if list:
                block = cursor.block()
                if cursor.position() - block.position() == LIST_PADDING_LENGTH:
                    it = block.begin()
                    if it.fragment().text().startswith(LIST_PADDING):
                        self.toggle_list()
                        return

        elif event.key() == Qt.Key.Key_Minus:
            cursor = self.textCursor()
            block = cursor.block()
            list = cursor.currentList()
            if not list and cursor.position() - block.position() == 2 and block.length() == 3:
                it = block.begin()
                if it.fragment().text().startswith('--'):
                    # Create a horizontal ruler if the line starts with three dashes
                    self.make_horizontal_ruler()
                    return

        elif event.key() == Qt.Key.Key_Space:
            cursor = self.textCursor()
            block = cursor.block()
            list = cursor.currentList()
            if not list and cursor.position() - block.position() == 1:
                it = block.begin()
                if it.fragment().text().startswith('*'):
                    # Create a new list if a line starts with an asterisk and a space
                    local_cursor = QTextCursor(cursor)
                    local_cursor.beginEditBlock()
                    local_cursor.setPosition(block.position())
                    local_cursor.setPosition(block.position() + 1, QTextCursor.MoveMode.KeepAnchor)
                    local_cursor.removeSelectedText()
                    self.toggle_list()
                    local_cursor.endEditBlock()
                    return

        elif event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
            without_modifers = [
                Qt.KeyboardModifier.ShiftModifier,
                Qt.KeyboardModifier.ControlModifier,
                Qt.KeyboardModifier.AltModifier,
                Qt.KeyboardModifier.MetaModifier]
            if not any(modifier & event.modifiers() for modifier in without_modifers):
                direction = {Qt.Key.Key_Left: QTextCursor.MoveOperation.Left,
                             Qt.Key.Key_Right: QTextCursor.MoveOperation.Right,
                             Qt.Key.Key_Up: QTextCursor.MoveOperation.Up,
                             Qt.Key.Key_Down: QTextCursor.MoveOperation.Down}
                if self._move_cursor(direction[event.key()]):
                    return

        self._ctrl_pressed = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        self._anchor = self.anchorAt(self.viewport().mapFromGlobal(QCursor.pos()))
        if self._anchor and self._ctrl_pressed:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
        else:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)

        QTextEdit.keyPressEvent(self, event)

    def _move_cursor(self, op: QTextCursor.MoveOperation) -> bool:
        """
        Navigates the cursor in the direction of the pressed key.
        The purpose of this function is to customize the behavior when navigating over lists.

        Returns true, when the move operation has been handled.
        """
        MoveOp = QTextCursor.MoveOperation
        MoveMode = QTextCursor.MoveMode

        cursor = QTextCursor(self.textCursor())
        pos = self.textCursor().position()
        block = cursor.block()
        layout = block.layout()
        line = layout.lineForTextPosition(cursor.positionInBlock())
        mode = MoveMode.MoveAnchor

        # Determine new cursor position
        if op in [MoveOp.Left, MoveOp.Right]:
                cursor.movePosition(op, mode)
                block = cursor.block()
                new_pos = cursor.position()
        elif op in [MoveOp.Up, MoveOp.Down]:
            if self._cursor_x == -1:
                self._set_cursor_x(cursor)
            self._keep_cursor_x = True
            if op == MoveOp.Up:
                i = line.lineNumber() - 1
                if i == -1:
                    block = block.previous()
                    layout = block.layout()
                    i = layout.lineCount() - 1 if layout is not None else 0
            else:
                i = line.lineNumber() + 1
                if i >= layout.lineCount():
                    block = block.next()
                    layout = block.layout()
                    i = 0
            if layout is None:
                # If layout is None it means that the cursor reached the top or the
                # bottom of the document. No move operation necessary here!
                return True
            if layout.lineCount() != 0:
                line = layout.lineAt(i)
                new_pos = block.position() + line.xToCursor(self._cursor_x)
            else:
                new_pos = block.position()
        else:
            return False

        # Skip over whitespaces after list bullet
        list = block.textList()
        if list:
            if new_pos - block.position() < LIST_PADDING_LENGTH:
                it = block.begin()
                if it.fragment().text().startswith(LIST_PADDING):
                    if op == MoveOp.Left and block.position() > 0:
                        new_pos = block.position() - 1
                    else:
                        new_pos = block.position() + LIST_PADDING_LENGTH

        if new_pos == pos:
            # The position hasn't changed
            return False

        # Set cursor position
        cursor.setPosition(new_pos)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        return True

    def _set_cursor_x(self, cursor: QTextCursor):
        block = cursor.block()
        layout = block.layout()
        pos = cursor.position() - block.position()

        line = layout.lineForTextPosition(pos)
        if line.isValid():
            self._cursor_x = line.cursorToX(pos)[0]
        else:
            self._cursor_x = -1

    def keyReleaseEvent(self, event: QKeyEvent):
        if self._ctrl_pressed and ~event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._ctrl_pressed = False
            QGuiApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
        QTextEdit.keyReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        if not self._ctrl_pressed and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._ctrl_pressed = True
        self._anchor = self.anchorAt(event.pos())
        if self._anchor and self._ctrl_pressed:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
        else:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
        QTextEdit.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        if not self._ctrl_pressed and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._ctrl_pressed = True
        self._anchor = self.anchorAt(event.pos())
        if self._anchor and self._ctrl_pressed:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
        else:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
        QTextEdit.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if not self._ctrl_pressed and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._ctrl_pressed = True
        self._anchor = self.anchorAt(event.pos())
        if self._anchor and self._ctrl_pressed:
            if len(self._anchor) > 8 and self._anchor[:8] == 'https://':
                url = self._anchor

                self._anchor = None
                self._ctrl_pressed = False
                QGuiApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)

                webbrowser.open(url)

                return

            elif len(self._anchor) > 7 and self._anchor[:7] == 'file://':
                filename = self._anchor[7:]

                self._anchor = None
                self._ctrl_pressed = False
                QGuiApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)

                self._system_open_file(self.root_directory, filename)

                return

        elif self._anchor:
            return
        QTextEdit.mouseReleaseEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        cursor = self.textCursor()
        local_cursor = self.cursorForPosition(event.pos())

        char_fmt = local_cursor.charFormat()
        if not char_fmt.isAnchor():
            return QTextEdit.mouseDoubleClickEvent(self, event)

        hyperlink = self._get_link_under_cursor(local_cursor)
        if hyperlink is None:
            return QTextEdit.mouseDoubleClickEvent(self, event)

        if (cursor.selectionStart() == hyperlink.position and 
            cursor.selectionEnd()   == hyperlink.position + hyperlink.length):
            local_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        else:
            local_cursor.setPosition(hyperlink.position)
            local_cursor.setPosition(hyperlink.position + hyperlink.length, QTextCursor.MoveMode.KeepAnchor)

        self.setTextCursor(local_cursor)

    def contextMenuEvent(self, event):
        menu = self.context_menu

        cursor = self.cursorForPosition(event.pos())
        hyperlink = self._get_link_under_cursor(cursor)
        is_link = hyperlink is not None

        self.edit_link_action.setData(hyperlink)
        self.edit_link_action.setVisible(is_link)
        self.edit_link_action.setEnabled(is_link)
        self.menu_separator_action.setVisible(is_link)

        menu.exec(event.globalPos())

    # -----------------------------------------------
    # 9. Clipboard functions
    # -----------------------------------------------

    def copy(self):
        """
        Override the copy function to generate custom HTML mime data that includes indent levels,
        headings, and list points.
        """
        mime_data = QMimeData()
        cursor = self.textCursor()

        # Export text as HTML
        selection_as_html = HtmlExporter(self.document(), cursor).output
        mime_data.setData("text/html", bytearray(selection_as_html, encoding="utf-8"))

        # Export text as plain
        fragment = QTextDocumentFragment(cursor)
        mime_data.setText(fragment.toPlainText())

        QGuiApplication.clipboard().setMimeData(mime_data)

    def copy_as_markdown(self):
        """
        Copy the whole document as a Markdown string.
        """
        mime_data = QMimeData()

        # Export text as Markdown
        markdown = MarkdownExporter(self.document()).output
        mime_data.setText(markdown)
        mime_data.setData("text/markdown", bytearray(markdown, encoding="utf-8"))

        QGuiApplication.clipboard().setMimeData(mime_data)

    def paste(self):
        cursor = self.textCursor()
        fragment = None

        mime_data = QGuiApplication.clipboard().mimeData()
        if mime_data.hasHtml():
            content_doc = HtmlImporter(mime_data.data('text/html').data().decode('utf-8')).document
            fragment = QTextDocumentFragment(content_doc)
        else:
            text = mime_data.text()
            if text:
                fragment = QTextDocumentFragment.fromPlainText(text)

        if fragment is not None:
            cursor.insertFragment(fragment)
        self.ensureCursorVisible()

    def cut(self):
        """
        Analogous to the copy function:
        Override the cut function to generate custom HTML mime data that includes indent levels,
        headings, and list points.
        """
        mime_data = QMimeData()
        cursor = self.textCursor()

        # Export text as HTML
        selection_as_html = HtmlExporter(self.document(), cursor).output
        mime_data.setData('text/html', bytearray(selection_as_html, encoding='utf-8'))

        # Export text as plain
        fragment = QTextDocumentFragment(cursor)
        mime_data.setText(fragment.toPlainText())

        cursor.removeSelectedText()

        QGuiApplication.clipboard().setMimeData(mime_data)

    def _clipboard_update(self):
        self.paste_action.setEnabled(self.canPaste())


class TextEditorWidget(QWidget):
    # -----------------------------------------------
    # 1. Constructor / Initialization
    # -----------------------------------------------

    def __init__(self, parent: QWidget=None):
        QWidget.__init__(self, parent)

        # Setup layout with toolbar and textedit
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Initialize toolbar widget
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 26))
        self.toolbar.setStyleSheet("QToolBar { spacing: 0px; }")
        layout.addWidget(self.toolbar)

        # Initialize TextEditor
        self.textedit = TextEditor(self)
        self.textedit.font_changed.connect(self._on_font_changed)
        self.textedit.block_format_changed.connect(self._on_blockformat_changed)
        layout.addWidget(self.textedit)

        # Setup toolbuttons
        # This happens after self.textedit is initialized, because it uses its actions, slots and other methods
        self._setup_toolbar()

        self.setLayout(layout)

    def _add_tool_button(self, img_name, action: QAction) -> GradientButton:
        btn = GradientButton(QImage(f'icons/fontawesome/{img_name}-24.png', 'PNG'),
                             base_color=QColor('#ebebeb'),
                             checked_color=QColor('#c7c7c7'))
        if not action.isEnabled():
            btn.setEnabled(False)
        if action.isCheckable():
            btn.set_checkable(True)
        action.changed.connect(lambda: btn.setEnabled(action.isEnabled()))
        action.toggled.connect(btn.set_checked)
        btn.clicked.connect(action.trigger)
        if len(action.text()) > 0:
            tooltip = action.text()
            if action.shortcut().toString() != '':
                tooltip += f' ({action.shortcut().toString()})'
            btn.setToolTip(tooltip)
        self.toolbar.addWidget(btn)
        return btn

    def _load_icon_image(self, icon_name: str):
        filepath = f"icons/fontawesome/{icon_name}-24.png"

        if not os.path.exists(filepath):
            filepath = f"icons/{icon_name}-24.png"

        return QImage(filepath, "PNG")

    def _add_ext_tool_button(self, icon_name: str, clicked_fnc=None, enabled=True,
                             checkable=False, tooltip: str = None) -> GradientButton:

        btn = GradientButton(self._load_icon_image(icon_name),
                             base_color=QColor('#ebebeb'),
                             checked_color=QColor('#c7c7c7'))
        if not enabled:
            btn.setEnabled(False)
        if checkable:
            btn.set_checkable(True)
        if clicked_fnc is not None:
            btn.clicked.connect(clicked_fnc)
        if tooltip is not None:
            btn.setToolTip(tooltip)
        self.toolbar.addWidget(btn)
        return btn

    def _add_separator(self):
        self.toolbar.addWidget(ToolBarSeparator())

    def _setup_toolbar(self):
        self._add_separator()

        # Undo / Redo
        self.undo_button = self._add_tool_button('undo', self.textedit.undo_action)
        self.redo_button = self._add_tool_button('redo', self.textedit.redo_action)

        self._add_separator()

        # Char format styles
        self.bold_button = self._add_tool_button('bold', self.textedit.text_bold_action)
        self.italic_button = self._add_tool_button('italic', self.textedit.text_italic_action)
        self.underline_button = self._add_tool_button('underline', self.textedit.text_underline_action)

        self._add_separator()

        # Text size
        self.combo_size = QComboBox()
        self.combo_size.setObjectName('comboSize')
        self.combo_size.setMinimumWidth(80)
        self.toolbar.addWidget(self.combo_size)
        self.combo_size.setEditable(True)

        standard_sizes = QFontDatabase.standardSizes()
        for size in standard_sizes:
            if size > 72:
                break
            self.combo_size.addItem(str(size))
        self.combo_size.setCurrentIndex(standard_sizes.index(QGuiApplication.font().pointSize()))
        self.combo_size.textActivated.connect(self.textedit.change_text_size)

        self._add_separator()

        # Block styles
        self.heading_lvl1_button = self._add_ext_tool_button('heading1', lambda: self._set_heading_level(1),
                                                             checkable=True, tooltip=self.tr("Heading Level 1"))
        self.heading_lvl2_button = self._add_ext_tool_button('heading2', lambda: self._set_heading_level(2),
                                                             checkable=True, tooltip=self.tr("Heading Level 2"))
        self.heading_lvl3_button = self._add_ext_tool_button('heading3', lambda: self._set_heading_level(3),
                                                             checkable=True, tooltip=self.tr("Heading Level 3"))
        self.heading_lvl4_button = self._add_ext_tool_button('heading4', lambda: self._set_heading_level(4),
                                                             checkable=True, tooltip=self.tr("Heading Level 4"))
        self.remove_style_button = self._add_ext_tool_button('paragraph', self.textedit.remove_block_style,
                                                             tooltip=self.tr("Paragraph"))
        self.list_button = self._add_ext_tool_button('list_ul', self.textedit.toggle_list, checkable = True,
                                                     tooltip=self.tr("List"))

        self._add_separator()

        # Indent
        self.indent_more_button = self._add_tool_button('indent', self.textedit.more_indent_action)
        self.indent_less_button = self._add_tool_button('indent-flipped', self.textedit.less_indent_action)

        self._add_separator()

        # Insert link / emoji
        self.link_button = self._add_ext_tool_button('link', self.textedit.insert_hyperlink,
                                                     tooltip=self.tr("Insert link..."))
        self.emoji_button = self._add_tool_button('face-grin', self.textedit.insert_emoji_action)

        self._add_separator()

    # -----------------------------------------------
    # 2. Private methods - QTextEdit slots
    # -----------------------------------------------

    @pyqtSlot(QFont)
    def _on_font_changed(self, font):
        self.combo_size.setCurrentIndex(self.combo_size.findText(str(font.pointSize())))
        self.combo_size.setEditText(str(font.pointSize()))

    @pyqtSlot()
    def _on_blockformat_changed(self):
        cursor = self.textedit.textCursor()
        block_fmt = cursor.blockFormat()
        heading_lvl = block_fmt.headingLevel()
        has_list = cursor.currentList() is not None

        self.heading_lvl1_button.set_checked(heading_lvl == 1)
        self.heading_lvl2_button.set_checked(heading_lvl == 2)
        self.heading_lvl3_button.set_checked(heading_lvl == 3)
        self.heading_lvl4_button.set_checked(heading_lvl == 4)
        self.list_button.set_checked(has_list)

    # -----------------------------------------------
    # 3. Other methods
    # -----------------------------------------------

    def _set_heading_level(self, level):
        cursor = self.textedit.textCursor()
        block_fmt = cursor.blockFormat()
        current_lvl = block_fmt.headingLevel()

        if level != current_lvl:
            self.textedit.set_heading_level(level)

        else:
            # The button is automatically unchecked after being clicked
            # That's why it's necessary to set it to checked again
            # as long as the blockFormat has the according headingLevel
            match level:
                case 1:
                    self.heading_lvl1_button.set_checked(True)
                case 2:
                    self.heading_lvl2_button.set_checked(True)
                case 3:
                    self.heading_lvl3_button.set_checked(True)
                case 4:
                    self.heading_lvl4_button.set_checked(True)
