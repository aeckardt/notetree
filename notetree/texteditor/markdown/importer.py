from dataclasses import dataclass
from typing import Optional, List
import re

from PyQt6.QtGui import (QTextDocument, QTextCursor, QTextBlockFormat, QTextCharFormat, QTextFormat, QFont)

from notetree.texteditor.inlineformat.html_style import *
from notetree.texteditor.markdown.inlineparser import *
from notetree.texteditor.style import *

@dataclass
class BlockToken:
    class Type(int):
        heading = 0
        list_item = 1
        horizontal_rule = 2
        paragraph = 3
        blank = 4
    type: Type  # 'heading', 'list_item', 'paragraph', etc.
    level: Optional[int] = None   # For heading or list depth
    children: Optional[List["InlineNode"]] = None

class MarkdownImporter:
    """
    A lightweight minimal Markdown parser for loading richtext to a QTextDocument.
    Currently implemented features for this Markdown parser are:
    - headings (with hashtag)
    - unordered lists
    - inline styles like bold, italic (only with asterisk)
    - links
    - the HTML tags 'ins' for underline and 'span' for font-size changes
    Possible extensions should go along with extended funcionalities of the class TextEditor.
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
        # Parse input into tokens (which are technically already a tree)
        tokens = self._tokenize(self.input)

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

    def _render_blocks(self, cursor: QTextCursor, tokens: List[BlockToken]):
        Type = BlockToken.Type

        # Iterate over all block tokens.
        for token in tokens:
            # Add a new line for each block, except for the first.
            if not self.at_beginning:
                self._new_line(cursor)
            else:
                self.at_beginning = False

            if token.type == Type.list_item:
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

            elif token.type == Type.heading:
                # Adjust heading level and charformat
                self.block_fmt.setHeadingLevel(token.level)
                self.char_fmt.setFontWeight(QFont.Weight.Bold)
                self.char_fmt.setProperty(QTextCharFormat.Property.FontSizeAdjustment, 4 - token.level)

            elif token.type == Type.horizontal_rule:
                # Set horizontal rule property for this block
                self.block_fmt.setProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth, horizontal_ruler_width)
                if horizontal_ruler_color is not None:
                    self.block_fmt.setProperty(QTextFormat.Property.BackgroundBrush, horizontal_ruler_color)

            elif token.type == Type.paragraph:
                # Set indent level for paragraph
                self.block_fmt.setIndent(token.level)

            # For blanks there is nothing else to do!

            if token.children:
                # Render line nodes
                self._render_inlines(cursor, token.children)

            if token.type == Type.heading:
                # Revert char format before new block for better rendering of list bullets
                self.char_fmt.setFontWeight(QFont.Weight.Normal)
                self.char_fmt.clearProperty(QTextCharFormat.Property.FontSizeAdjustment)

            # Set blockformat for the current block before adding a new
            self._end_line(cursor)

    def _render_inlines(self, cursor: QTextCursor, nodes: List[InlineNode]):
        Type = InlineNode.Type

        def apply_node_style(node: InlineNode, char_format: QTextCharFormat):
            if node.type == Type.strong:
                char_format.setFontWeight(QFont.Weight.Bold)
            elif node.type == Type.emph:
                char_format.setFontItalic(True)
            elif node.type == Type.inline_link:
                char_format.setAnchor(True)
                char_format.setAnchorHref(node.attrs['href'])
                char_format.setForeground(LINK_COLOR)
            elif node.type == Type.html_tag:
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
            if token.type == Type.text:
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

    def _tokenize(self, markdown_input: str) -> List[BlockToken]:
        Type = BlockToken.Type

        lines = markdown_input.splitlines()
        tokens = []
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            if match := re.match(r'^(#{1,4})\s+(.*)', stripped):
                content = match.group(2)
                tokens.append(BlockToken(
                    type=Type.heading,
                    level=len(match.group(1)),
                    children=self._parse_inline(content)
                ))
            elif re.match(r'^[-*]\s+', stripped):
                content = re.sub(r'^[-*]\s+', '', stripped)
                tokens.append(BlockToken(
                    type=Type.list_item,
                    level=indent // 2,  # 2-space indentation = one level
                    children=self._parse_inline(content)
                ))
            elif stripped == '---':
                tokens.append(BlockToken(type=Type.horizontal_rule))
            elif stripped == '':
                # empty line → paragraph break
                tokens.append(BlockToken(type=Type.blank))
            else:
                level = indent // 4  # 4-space indentation = one level
                content = line[level * 4:]
                tokens.append(BlockToken(
                    type=Type.paragraph,
                    level=level,
                    children=self._parse_inline(content)
                ))
        return tokens

    def _parse_inline(self, text: str) -> List[InlineNode]:
        return MarkdownInlineParser(text).ast_root.children
