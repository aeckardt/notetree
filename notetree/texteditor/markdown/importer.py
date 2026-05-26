from dataclasses import dataclass
from enum import IntEnum
import re

from PyQt6.QtGui import (QTextDocument, QTextCursor, QTextBlockFormat, QTextCharFormat, QTextFormat, QFont)

from notetree.texteditor.inlineformat.html_style import *
from notetree.texteditor.markdown.inlineparser import MarkdownInlineParser, InlineNode
from notetree.texteditor.style import *

@dataclass
class BlockToken:
    class Type(IntEnum):
        HEADING = 0
        LIST_ITEM = 1
        HORIZONTAL_RULE = 2
        PARAGRAPH = 3
        BLANK = 4
    type: Type  # 'HEADING', 'LIST_ITEM', 'PARAGRAPH', etc.
    level: int | None = None   # For heading or list depth
    children: list["InlineNode"] | None = None

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)")
UNORDERED_LIST_RE = re.compile(r"^[-*]\s+(.*)")
HORIZONTAL_RULE = "---"

class MarkdownImporter:
    """
    Imports NoteTree's Markdown focused subset into a QTextDocument.

    Supported block elements:
    - headings levels 1-4
    - unordered list items
    - horizontal rules
    - paragraphs and blank lines

    Inline content is parsed by MarkdownInlineParser, including emphasis,
    links, underline tags and supported span styles.

    The supported syntax follows the current TextEditor feature set
    rather than full CommonMark compatibility.
    """

    def __init__(self, markdown_input: str):
        global default_char_format
        if not default_char_format:
            default_char_format = init_default_char_format()

        self.input = markdown_input
        self.document = self._import()

    def _import(self) -> QTextDocument:
        """
        Imports the Markdown input either into a new document.
        You can insert the document to an existing one using QTextDocumentFragment.
        """
        # Parse input into block tokens (which are technically already a tree)
        tokens = self._parse_blocks(self.input)

        # Create new document
        document = QTextDocument()
        cursor = QTextCursor(document)

        # Do not create an undo when creating the new document from the input
        document.setUndoRedoEnabled(False)

        cursor.beginEditBlock()

        self.block_fmt = QTextBlockFormat(default_block_format)
        self.char_fmt = QTextCharFormat(default_char_format)

        self.at_beginning = True
        self.current_list = None

        # Render all the tokens onto the cursor
        self._render_blocks(cursor, tokens)

        cursor.endEditBlock()

        # Restore undoRedoEnabled
        document.setUndoRedoEnabled(True)

        return document

    def _render_blocks(self, cursor: QTextCursor, tokens: list[BlockToken]):
        Type = BlockToken.Type

        # Iterate over all block tokens
        for token in tokens:
            # Add a new line for each block, except for the first
            if not self.at_beginning:
                self._new_line(cursor)
            else:
                self.at_beginning = False

            if token.type == Type.LIST_ITEM:
                # Insert two spaces, because the bullet is usually pretty tightly squeezed onto the text
                # And there is unfortunately no simple styling that can change that
                cursor.insertText('  ', QTextCharFormat(default_char_format))

                if not self.current_list:
                    if cursor.currentList():
                        self.current_list = cursor.currentList()
                    else:
                        # Setup list, if not yet available
                        self.current_list = cursor.createList(QTextListFormat.Style.ListDisc)

                # Set object index for block format
                self.block_fmt.setObjectIndex(self.current_list.objectIndex())
                self.block_fmt.setIndent(token.level)

                # Set list style dependent on indent
                if token.level > 0:
                    self.block_fmt.setProperty(QTextFormat.Property.ListStyle, LOWER_LEVEL_LIST_STYLE)
                else:
                    self.block_fmt.setProperty(QTextFormat.Property.ListStyle, TOP_LEVEL_LIST_STYLE)

                # Add item to list
                self.current_list.add(cursor.block())

            elif token.type == Type.HEADING:
                # Adjust heading level and charformat
                self.block_fmt.setHeadingLevel(token.level)
                self.char_fmt.setFontWeight(QFont.Weight.Bold)
                self.char_fmt.setProperty(QTextCharFormat.Property.FontSizeAdjustment, 4 - token.level)

            elif token.type == Type.HORIZONTAL_RULE:
                # Set horizontal rule property for this block
                self.block_fmt.setProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth, horizontal_ruler_width)
                if horizontal_ruler_color is not None:
                    self.block_fmt.setProperty(QTextFormat.Property.BackgroundBrush, horizontal_ruler_color)

            elif token.type == Type.PARAGRAPH:
                # Set indent level for paragraph
                self.block_fmt.setIndent(token.level)

            # For blanks there is nothing else to do
            # Since a new line has already been added

            if token.children:
                # Render line nodes
                self._render_inlines(cursor, token.children)

            if token.type == Type.HEADING:
                # Revert char format before new block for better rendering of list bullets
                self.char_fmt.setFontWeight(QFont.Weight.Normal)
                self.char_fmt.clearProperty(QTextCharFormat.Property.FontSizeAdjustment)

            # Set blockformat for the current block before adding a new
            self._end_line(cursor)

    def _render_inlines(self, cursor: QTextCursor, nodes: list[InlineNode]):
        Type = InlineNode.Type

        def apply_node_style(node: InlineNode, char_format: QTextCharFormat):
            if node.type == Type.STRONG:
                char_format.setFontWeight(QFont.Weight.Bold)
            elif node.type == Type.EMPH:
                char_format.setFontItalic(True)
            elif node.type == Type.INLINE_LINK:
                char_format.setAnchor(True)
                char_format.setAnchorHref(node.attrs['href'])
                char_format.setForeground(LINK_COLOR)
            elif node.type == Type.HTML_TAG:
                match node.content:
                    case 'ins':
                        char_format.setFontUnderline(True)
                    case 'span':
                        if not node.attrs or not 'style' in node.attrs:
                            # Ignore the span
                            return

                        # Apply span style to char format
                        style = parse_properties(node.attrs['style'])
                        apply_html_style(style, char_format)

        # Render inline tokens recursively
        for token in nodes:
            if token.type == Type.TEXT:
                cursor.insertText(token.content, self.char_fmt)
            elif token.children:
                # Save current format and apply changes
                old_fmt = QTextCharFormat(self.char_fmt)
                apply_node_style(token, self.char_fmt)

                # Change char format for this bracket
                cursor.setCharFormat(self.char_fmt)

                # Iterate over children
                self._render_inlines(cursor, token.children)

                # Restore previous char format
                self.char_fmt = old_fmt
                cursor.setCharFormat(self.char_fmt)

    def _new_line(self, cursor: QTextCursor):
        # Add new block
        cursor.insertBlock()

        # Reset block format
        self.block_fmt = QTextBlockFormat(default_block_format)

        # Reset char format (now with default font size)
        self.char_fmt = QTextCharFormat(default_char_format)
        cursor.setCharFormat(self.char_fmt)

    def _end_line(self, cursor: QTextCursor):
        # Set block format with indent and heading level
        cursor.setBlockFormat(self.block_fmt)

        # Setting the char format at the end of the line can affect rendering
        cursor.setCharFormat(self.char_fmt)

    def _parse_blocks(self, markdown_input: str) -> list[BlockToken]:
        lines = markdown_input.splitlines()
        return [self._parse_block_line(line) for line in lines]

    def _parse_block_line(self, line: str) -> BlockToken:
        """
        Parse one physical Markdown line into one block token.

        This method only determines the block type and indentation level.
        Inline formatting for paragraphs is delegated to MarkdownInlineParser.
        """
        BlockType = BlockToken.Type

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Headings must be recognized before paragraphs. NoteTree currently
        # supports heading levels 1-4.
        if match := HEADING_RE.match(stripped):
            content = match.group(2)
            return BlockToken(
                type=BlockType.HEADING,
                level=len(match.group(1)),
                children=self._parse_inline(content),
            )

        # Unordered list items use two spaces as one nesting level. This
        # matches the indentation behavior used by the TextEditor.
        if match := UNORDERED_LIST_RE.match(stripped):
            content = match.group(1)
            return BlockToken(
                type=BlockType.LIST_ITEM,
                level=indent // 2,
                children=self._parse_inline(content),
            )

        # A horizontal rule is only recognized in the exact form exported
        # by NoteTree.
        if stripped == HORIZONTAL_RULE:
            return BlockToken(type=BlockType.HORIZONTAL_RULE)

        # Blank lines are preserved as empty blocks.
        if not stripped:
            return BlockToken(type=BlockType.BLANK)

        # Indented text is a paragraph.
        level = indent // 4
        content = line[level * 4:]
        return BlockToken(
            type=BlockType.PARAGRAPH,
            level=level,
            children=self._parse_inline(content),
        )

    def _parse_inline(self, text: str) -> list[InlineNode]:
        return MarkdownInlineParser(text).ast_root.children
