from dataclasses import dataclass
import re
import urllib.parse

from PyQt6.QtGui import (QTextDocument, QTextFormat, QTextCursor, QTextBlock)

from notetree.texteditor.inlineformat.resolver import (ExportableFragment, Format as InlineFormat,
                                                       InlineFormatResolver)
from notetree.texteditor.style import LIST_PADDING, LIST_PADDING_LENGTH

@dataclass
class Tag:
    name: str
    attrs: dict | None = None

TagStack = list[Tag]

class MarkdownExporter:
    """
    Convert the specified QTextDocument range to NoteTree Markdown.

    The exporter writes the Markdown constructs currently supported by
    NoteTree's TextEditor, including headings, unordered lists, inline
    styling, links, horizontal rules and supported font-size spans.
    """
    def __init__(self, document: QTextDocument, range: QTextCursor = None):
        self.document = document
        if range is None:
            # Export the whole document
            self._start = 0
            lastBlock = document.lastBlock()
            if lastBlock is None:
                self.output = ''
                self._end = -1
            else:
                self._end = lastBlock.position() + lastBlock.length()
        else:
            # Export the selection
            self._start = range.selectionStart()
            self._end = range.selectionEnd()

        self.output = self._export()

    def _export(self) -> str:
        if self._end < self._start:
            return ''

        # Initialize output
        lines = []

        # Set block to where the range starts
        local_cursor = QTextCursor(self.document)
        local_cursor.setPosition(self._start)
        block = local_cursor.block()

        # Initialize open block tags
        self._open_block_tags = TagStack()

        while block.isValid() and block.position() < self._end:
            # Export the block (generate Markdown for the block)
            lines.append(self._export_block(block))

            # Advance to the next block
            block = block.next()

        return '\n'.join(lines)

    def _export_block(self, block: QTextBlock) -> str:
        block_format = block.blockFormat()
        heading_level = block_format.headingLevel()
        text_list = block.textList()

        # Check for horizontal rule
        horizontal_rule = block_format.hasProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth)
        if horizontal_rule:
            return '---'

        # Build prefix from block format
        if text_list:
            indent = "  " * block_format.indent()
            prefix = f'{indent}* '
            return prefix + self._export_inline_content(
                block,
                remove_two_spaces=True,
            )

        if 1 <= heading_level <= 4:
            prefix = f'{"#" * heading_level} '
            return prefix + self._export_inline_content(
                block,
                remove_two_spaces=False,
                heading_level=heading_level,
            )

        return self._export_inline_content(
            block,
            remove_two_spaces=False,
        )

    def _export_block(self, block: QTextBlock) -> str:
        block_format = block.blockFormat()
        heading_level = block_format.headingLevel()
        text_list = block.textList()

        # Check for horizontal rule
        horizontal_rule = block_format.hasProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth)
        if horizontal_rule:
            return '---'

        # Build prefix from block format
        if text_list:
            # Two spaces per list indent level
            indent = "  " * block_format.indent()
            prefix = f"{indent}* "
        elif 1 <= heading_level <= 4:
            prefix = f"{'#' * heading_level} "
        else:
            prefix = ""

        # Resolve inline formats to be in the right order
        fragments = InlineFormatResolver(block, self._start, self._end).fragments

        # Process each fragment in the block
        line_text = ''
        at_block_begin = True
        it = block.begin()
        for fragment in fragments:
            if not fragment.fragment.isValid():
                break

            fragment_text, remaining = self._export_fragment(fragment, at_block_begin and text_list,
                                                             heading_level)
            line_text += fragment_text

            if remaining <= 0:
                break

            it += 1
            at_block_begin = False

        return prefix + line_text

    def _export_fragment(self, ef: ExportableFragment, remove_two_spaces: bool,
                         heading_level: int = 0) -> str:
        Type = InlineFormat.Type

        fragment = ef.fragment
        text = fragment.text()

        # Remove two leading spaces from text, if it's a list point
        # They are automatically added for the sake of aesthetics
        if remove_two_spaces and text.startswith(LIST_PADDING):
            text = text[LIST_PADDING_LENGTH:]

        # Calculate selection boundaries within this fragment
        slice_left = max(0, self._start - fragment.position())
        remaining = self._end - fragment.position() - fragment.length()
        slice_right = None if remaining >= 0 else remaining
        selected_text = text[slice_left:None if slice_right == 0 else slice_right]

        # Detect leading/trailing spaces
        leading_ws = re.match(r'^\s*', selected_text).group()
        trailing_ws = re.search(r'\s*$', selected_text).group()
        core_text = selected_text[len(leading_ws):len(selected_text)-len(trailing_ws) or None]

        # Gather opening and closing tokens
        opening_tokens = []
        closing_tokens = []
        for fmt_change in ef.fmt_changes:
            # Don't export font size changes if block format is a heading
            if heading_level > 0 and fmt_change.type in [Type.bold, Type.pointsize]:
                continue

            match fmt_change.type:
                case Type.bold:
                    if fmt_change.open:
                        opening_tokens.append('**')
                    else:
                        closing_tokens.append('**')
                case Type.italic:
                    if fmt_change.open:
                        opening_tokens.append('*')
                    else:
                        closing_tokens.append('*')
                case Type.underline:
                    if fmt_change.open:
                        opening_tokens.append('<ins>')
                    else:
                        closing_tokens.append('</ins>')
                case Type.pointsize:
                    if fmt_change.open:
                        opening_tokens.append(f'<span style="font-size:{fmt_change.attrs['font-size']}pt">')
                    else:
                        closing_tokens.append('</span>')
                case Type.link:
                    if fmt_change.open:
                        opening_tokens.append('[')
                    else:
                        escaped_href = urllib.parse.quote(fmt_change.attrs['href'], safe=':/')
                        closing_tokens.append(f']({escaped_href})')

        # Apply formatting only to core
        core_text = ''.join(opening_tokens) + core_text + ''.join(closing_tokens)
        return leading_ws + core_text + trailing_ws, remaining
