from dataclasses import dataclass
import html

from PyQt6.QtGui import (QTextDocument, QTextCursor, QTextBlock, QTextFormat)

from notetree.texteditor.inlineformat.resolver import ExportableFragment, Format as InlineFormat, InlineFormatResolver
from notetree.texteditor.style import style_module

@dataclass
class Tag:
    name: str
    attrs: dict | None = None

TagStack = list[Tag]

class HtmlExporter:
    """
    Convert the specified range of the QTextDocument into HTML.
    This class builds minimal HTML code that includes CSS styling
    for paragraphs, headings, and list indents.
    """
    def __init__(self, document: QTextDocument, range: QTextCursor = None, skip_header: bool = False):
        self.document = document
        if range is None:
            # Export the whole document
            self._start = 0
            lastBlock = document.lastBlock()
            if lastBlock is None:
                return ''
            else:
                self._end = lastBlock.position() + lastBlock.length()
        else:
            # Export the selection
            self._start = range.selectionStart()
            self._end = range.selectionEnd()
        self.skip_header = skip_header

        self.output = self._export()

    def _export(self) -> str:
        if self._end < self._start:
            return ''

        html_output = ''
        if not self.skip_header:
            # Create the basic HTML header and style definitions.
            html_output += HtmlExporter._get_html_header()

        # Set block to where the range starts
        local_cursor = QTextCursor(self.document)
        local_cursor.setPosition(self._start)
        block = local_cursor.block()

        # Initialize open block tags
        self._open_block_tags = TagStack()

        while block.isValid() and block.position() <= self._end:
            # Export the block (generate HTML for the block)
            html_output += self._export_block(block) + '\n'

            # Advance to the next block
            block = block.next()

        if not self.skip_header:
            # Add footer
            html_output += HtmlExporter._get_html_footer()
        elif html_output and html_output[-1] == '\n':
            # Remove last newline
            html_output = html_output[:-1]

        return html_output

    def _export_block(self, block: QTextBlock) -> str:
        # Open the block (generate starting HTML for the block)
        line_html = HtmlExporter._block_format_to_html(block, self._open_block_tags, self._end, True)

        # Resolve char formats
        fragments = InlineFormatResolver(block, self._start, self._end).fragments
 
        # Process each fragment in the block
        at_block_begin = True
        it = block.begin()
        for ef in fragments:
            fragment = ef.fragment
            if not fragment.isValid():
                break

            text = fragment.text()

            # Remove two leading spaces from text, if it's a list point
            # They are automatically added for the sake of aesthetics
            if at_block_begin and block.textList() and text.startswith('  '):
                text = text[2:]

            # Calculate selection boundaries within this fragment
            slice_left = max(0, self._start - fragment.position())
            remaining = self._end - fragment.position() - fragment.length()
            slice_right = None if remaining >= 0 else remaining
            selected_text = text[slice_left:None if slice_right == 0 else slice_right]

            # For non-heading blocks, wrap each fragment with its char format.
            if block.blockFormat().headingLevel() == 0:
                line_html += HtmlExporter._inline_format_to_html(ef, True)

            # Add selected text within fragment
            line_html += html.escape(selected_text)

            # For non-heading blocks, close formatting tags
            if block.blockFormat().headingLevel() == 0:
                line_html += HtmlExporter._inline_format_to_html(ef, False)

            if remaining <= 0:
                break

            it += 1
            at_block_begin = False

        # Close the block's formatting.
        line_html += HtmlExporter._block_format_to_html(block, self._open_block_tags, self._end, False)
        return line_html

    @staticmethod
    def _block_format_to_html(block: QTextBlock, open_tags: TagStack, end_pos, open: bool) -> str:
        """
        Build HTML for a block (paragraph, heading, or list item).
        Uses the open_tags stack to track which tags are open.
        Uses inline CSS to represent indent via margin-left.
        """
        block_format = block.blockFormat()
        indent_level = block_format.indent()  # Integer indent level
        indent_style = f' style="-qt-block-indent: {indent_level};"' if indent_level > 0 else ""

        nested_ul_tags = sum(1 for tag in open_tags if tag.name == 'ul')

        # When opening a block, add the appropriate tag and push it to open_tags.
        if open:
            # Handle headings (if headingLevel > 0)
            if block_format.hasProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth):
                return '<hr width="60%"/>'

            if block_format.headingLevel() > 0:
                heading_tag = f'h{block_format.headingLevel()}'
                open_tags.append(Tag(heading_tag))
                return f'<{heading_tag}{indent_style}>'

            # Handle list items
            elif block.textList():
                output = ""

                # Determine how many nested <ul> tags are needed.
                # Convention: we assume that each block's indent corresponds to (indent_level + 1) levels.
                while nested_ul_tags < (indent_level + 1):
                    open_tags.append(Tag("ul"))
                    output += '<ul>'
                    nested_ul_tags += 1

                # Now, open the list item.
                open_tags.append(Tag("li"))
                output += '<li>'

                return output
            else:
                # Otherwise, treat as a regular paragraph.
                open_tags.append(Tag("p"))
                return f'<p{indent_style}>'
        else:
            # Closing tags for this block.
            output = ""

            # If a list item was opened, close it.
            if open_tags and open_tags[-1].name == "li":
                output += "</li>"
                open_tags.pop()

            # For list blocks, determine if subsequent blocks are part of the same list.
            if block.textList():
                # Look ahead to the next block; if the next block is a list,
                # adjust the number of open <ul> tags according to its indent.
                next_block = block.next()
                next_indent = 0
                if next_block.isValid() and next_block.position() < end_pos and next_block.textList():
                    next_indent = next_block.blockFormat().indent()

                    # Close extra <ul> tags if the current indent is higher.
                    while nested_ul_tags > (next_indent + 1):
                        output += "</ul>"
                        nested_ul_tags -= 1

                        # Remove the last occurrence of 'ul' from open_tags.
                        for i in reversed(range(len(open_tags))):
                            if open_tags[i].name == "ul":
                                del open_tags[i]
                                break

                    # Do not close if they match.
                else:
                    # If the next block is not a list, close all open <ul> tags.
                    while Tag("ul") in open_tags:
                        output += "</ul>"
                        open_tags.remove(Tag("ul"))
                return output
            else:
                # For paragraphs or headings, simply close all remaining block-level tags.
                while open_tags and open_tags[-1].name not in ["ul", "li"]:
                    tag = open_tags.pop()
                    output += f"</{tag.name}>"
                return output

    @staticmethod
    def _inline_format_to_html(fragment: ExportableFragment, open: bool) -> str:
        Type = InlineFormat.Type

        tags = []
        for fmt_change in fragment.fmt_changes:
            if open != fmt_change.open:
                continue
            match fmt_change.type:
                case Type.link:
                    tags.append(f'<a href="{fmt_change.attrs['href']}">' if open else '</a>')
                case Type.pointsize:
                    tags.append(f'<span style="font-size:{fmt_change.attrs['font-size']}pt">' if open else '</span>')
                case Type.bold:
                    tags.append('<strong>' if open else '</strong>')
                case Type.italic:
                    tags.append('<em>' if open else '</em>')
                case Type.underline:
                    tags.append('<ins>' if open else '</ins>')
        
        return ''.join(tags)

    @staticmethod
    def _get_html_header() -> str:
        block_tags = ['p', 'li', 'h1', 'h2', 'h3', 'h4']
        all_tags = list(set(block_tags + ['ul']))

        # Optional styles
        line_height = getattr(style_module, 'BLOCK_LINE_HEIGHT', None)
        margin_top = getattr(style_module, 'BLOCK_TOP_MARGIN', None)
        margin_bottom = getattr(style_module, 'BLOCK_BOTTOM_MARGIN', None)

        # Build tag styles
        tag_styles = {}
        for tag in all_tags:
            styles = {}
            if tag in all_tags:
                if line_height is not None:
                    styles['line-height'] = f'{line_height}'
            if tag in block_tags:
                if margin_top is not None and tag in block_tags:
                    styles['margin-top'] = f'{margin_top}px'
                if margin_bottom is not None and tag in block_tags:
                    styles['margin-bottom'] = f'{margin_bottom}px'
            tag_styles[tag] = styles

        # Group tags with identical styles
        # Use the style string as a dict key
        grouped_styles = {}
        for tag, styles in tag_styles.items():
            style_str = '; '.join(f'{k}: {v}' for k, v in styles.items())
            grouped_styles.setdefault(style_str, []).append(tag)

        # Convert grouped styles to CSS
        css_rules = []
        for style_str, tags in grouped_styles.items():
            selector = ', '.join(tags)
            css_rules.append(f'{selector} {{ {style_str}; }}')

        # Assemble final HTML header
        return (
            '<!DOCTYPE html>\n'
            '<html>\n'
            '<head>\n'
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n'
            '<style type="text/css">\n'
            'p, li { white-space: pre-wrap; }\n'
            + '\n'.join(css_rules) + '\n'
            '</style>\n'
            '</head>\n'
            '<body>\n'
        )

    @staticmethod
    def _get_html_footer() -> str:
        return (
            '</body>\n'
            '</html>'
        )
