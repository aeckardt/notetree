from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re
import html
import sys

from PyQt6.QtGui import (QTextDocument, QTextCursor, QTextBlockFormat, QTextCharFormat, QFont, QTextFormat)

from notetree.texteditor.inlineformat.html_style import *
from notetree.texteditor.style import *

@dataclass
class Token:
    class Type(int):
        start_tag = 0
        end_tag = 1
        text = 2
        self_closing_tag = 3
    type: Type  # start_tag, end_tag, text or self_closing_tag
    name: Optional[str] = None  # tag name
    attrs: Optional[dict] = None
    content: Optional[str] = None  # for text or comments

TAG_PATTERN = re.compile(
    r'(?P<tag><[^>]+>)|(?P<text>[^<]+)', re.DOTALL
)

ATTR_PATTERN = re.compile(
    r'(?P<name>[a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*'
    r'(?P<quote>["\'])(?P<value>.*?)(?P=quote)'
)

SELF_CLOSING_TAGS = {"br", "hr", "img", "meta"}

@dataclass
class HtmlNode:
    class Type(int):
        element = 0
        text = 1

    type: Type  # element or text
    name: Optional[str] = None  # tag name if element
    attrs: Optional[Dict[str, str]] = field(default_factory=dict)
    children: List["HtmlNode"] = field(default_factory=list)
    content: Optional[str] = None  # only for text nodes

class RenderContext:
    def __init__(self, styles = None, metadata = None):
        self.styles = styles or {}
        self.metadata = metadata or {}

    def get_style_for(self, node: HtmlNode):
        style: dict = self.styles.get(node.name, {}).copy()

        # Merge initial styles
        inline = node.attrs.get('style')
        if inline:
            style.update(self._parse_inline_style(inline))

        return style

    @staticmethod
    def _parse_inline_style(style_str: str) -> dict:
        """
        Parses an inline style string (e.g., "color: red; font-weight: bold;") into a dictionary.
        """
        styles = {}
        for property in style_str.split(';'):
            property = property.strip()
            if not property:
                continue
            if ':' not in property:
                continue
            name, value = property.split(':', 1)
            styles[name.strip()] = value.strip()
        return styles

class HtmlImporter:
    """
    A helper class for importing a QTextDocument from minimal HTML.
    The main purpose of this importer is to losslessly cut, copy and paste
    between QTextDocuments created with TextEditor.
    Therefore it doesn't parse a lot of tags and styles.
    Should be extended whenever suitable.
    """

    # -----------------------------------------------
    # 1. Import HTML into QTextDocument
    # -----------------------------------------------
    def __init__(self, html_input: str):
        global default_char_format, default_font_pointsize
        if not default_char_format:
            default_char_format = init_default_char_format()
            default_font_pointsize = init_default_font_pointsize()

        self.input = html_input
        self.document = self._import()

    def _import(self) -> QTextDocument:
        # Parse input into tokens
        tokens = list(self._tokenize(self.input)) # Convert to list to allow lookahead

        # Build syntax tree
        ast = self._parse(tokens)

        html_node = self._find_node(ast, 'html')
        if html_node is None:
            html_node = HtmlNode(HtmlNode.Type.element, 'html', children=ast)

        # Setup context for styles
        self.context = RenderContext()
        head_node = self._find_node(html_node, 'head')
        if head_node is not None:
            self._extract_context(head_node)

        body_node = self._find_node(html_node, 'body')
        if body_node is None:
            body_node = HtmlNode(HtmlNode.Type.element, 'body', children=ast)

        # Create new document
        document = QTextDocument()
        cursor = QTextCursor(document)

        # Do not create an undo when creating the new document from the input
        document.setUndoRedoEnabled(False)

        cursor.beginEditBlock()

        self.block_fmt = QTextBlockFormat(default_block_format)
        self.char_fmt = QTextCharFormat(default_char_format)

        self.at_beginning = True
        self.new_paragraph = False
        self.new_list_item = False
        self.indent = 0
        self.nested_ul_tags = 0
        self.current_list = None

        # Walk the AST and render each node
        self._render_node(cursor, body_node)

        cursor.endEditBlock()

        # Restore undoRedoEnabled
        document.setUndoRedoEnabled(True)

        return document

    # -----------------------------------------------
    # 2. Walk syntax tree and render nodes
    # -----------------------------------------------

    def _render_node(self, cursor: QTextCursor, node: HtmlNode):
        if node.type == HtmlNode.Type.text: # Text node
            if node.content:
                # Insert text with the current char format
                cursor.insertText(node.content, self.char_fmt)

                # Remove newline guards because text has been added
                self.new_paragraph = False
                self.new_list_item = False
            return

        # Indicates if self.char_fmt has been changed within this function
        fmt_changed = False

        # Handle tags
        tag = node.name.lower()
        match tag:
            case 'p':
                # Safety guard for not adding a new line directly after a list item
                if not self.new_list_item:
                    self._new_line(cursor)
                else:
                    self.new_list_item = False
                self.new_paragraph = True
            case 'br':
                if not self.new_paragraph:
                    self._end_line(cursor)
                    self._new_line(cursor)
                else:
                    # Don't add a new line if the paragraph just started
                    # Because a new line has already been added!
                    self.new_paragraph = False
                # Since br is a self enclosing tag, it's safe to return
                self._end_line(cursor)
                return
            case 'hr':
                if not self.new_paragraph:
                    self._end_line(cursor)
                    self._new_line(cursor)
                else:
                    # Don't add a new line if the paragraph just started
                    # Because a new line has already been added!
                    self.new_paragraph = False
                # Set horizontal rule property for this block
                self.block_fmt.setProperty(QTextFormat.Property.BlockTrailingHorizontalRulerWidth, horizontal_ruler_width)
                if horizontal_ruler_color is not None:
                    self.block_fmt.setProperty(QTextFormat.Property.BackgroundBrush, horizontal_ruler_color)
                # Since hr is a self enclosing tag, it's safe to return
                self._end_line(cursor)
                return
            case 'strong' | 'b':
                self.char_fmt.setFontWeight(QFont.Weight.Bold)
                fmt_changed = True
            case 'em' | 'i':
                self.char_fmt.setFontItalic(True)
                fmt_changed = True
            case 'ins' | 'u':
                self.char_fmt.setFontUnderline(True)
                fmt_changed = True
            case 'a':
                self.char_fmt.setAnchor(True)
                if 'href' in node.attrs:
                    self.char_fmt.setAnchorHref(node.attrs['href'])
                self.char_fmt.setForeground(LINK_COLOR)
                fmt_changed = True
            case 'ul':
                # Increase value for more indent (in case more than one ul tag is used)
                self.nested_ul_tags += 1
            case 'li':
                if self.nested_ul_tags <= 0:
                    print("Warning: Misplaced <li> tag. Lists might not be added properly.", file=sys.stderr)

                # Use new line for list item
                self._new_line(cursor)

                # If a new line has not been added, the cursor might not be at the block start
                if cursor.atBlockStart():
                    # Insert two spaces, because the bullet is usually pretty tightly squeezed onto the text
                    # And there is unfortunately no simple styling that can change that
                    cursor.insertText('  ', QTextCharFormat())

                if not self.current_list:
                    if cursor.currentList():
                        self.current_list = cursor.currentList()
                    else:
                        # Setup list, if not yet available
                        self.current_list = cursor.createList(QTextListFormat.Style.ListDisc)

                # Set object index for block format
                self.block_fmt.setObjectIndex(self.current_list.objectIndex())

                # Set list style dependent on indent
                if self.nested_ul_tags > 1:
                    self.block_fmt.setProperty(QTextFormat.Property.ListStyle, LOWER_LEVEL_LIST_STYLE)
                else:
                    self.block_fmt.setProperty(QTextFormat.Property.ListStyle, TOP_LEVEL_LIST_STYLE)

                # Add item to list
                self.current_list.add(cursor.block())

                # Activate safety guard to not add a new line with a paragraph directly after
                self.new_list_item = True
            case 'h1' | 'h2' | 'h3' | 'h4':
                # Use new line for heading
                self._new_line(cursor)

                # Adjust charformat
                heading_level = int(tag[1])
                self.block_fmt.setHeadingLevel(heading_level)
                self.char_fmt.setFontWeight(QFont.Weight.Bold)
                self.char_fmt.setProperty(QTextCharFormat.Property.FontSizeAdjustment, 4 - heading_level)
                fmt_changed = True

        # Handle styles
        style = self.context.get_style_for(node)

        # Apply styles to self.block_fmt
        self._apply_block_format_styles(style)

        # Apply styles to self.char_fmt
        fmt_changed = fmt_changed or apply_html_style(style, self.char_fmt)

        if self.new_paragraph and tag != 'p':
            # Remove guard for not adding a new line when a <br /> tag follows directly after a paragraph
            self.new_paragraph = False
        if self.new_list_item and tag != 'li':
            # Remove guard for not adding a new line when a <p> tag follows directly after a list item
            self.new_list_item = False

        # Change char format for the following bracket
        if fmt_changed:
            old_fmt = cursor.charFormat()
            cursor.setCharFormat(self.char_fmt)

        # Iterate over children
        self._render_children(cursor, node)

        # Restore previous char format
        if fmt_changed:
            self.char_fmt = old_fmt
            cursor.setCharFormat(self.char_fmt)

        # Handle closing tags
        match tag:
            case 'p':
                if not self.new_list_item:
                    self._end_line(cursor)
                self.new_paragraph = False
            case 'ul':
                self.nested_ul_tags -= 1
                if self.nested_ul_tags == 0:
                    # Remove list reference
                    self.current_list = None
                    self.block_fmt.setObjectIndex(-1)
            case 'li':
                self._end_line(cursor)
            case 'h1' | 'h2' | 'h3' | 'h4':
                self._end_line(cursor)
                self.block_fmt.setHeadingLevel(0)

    def _render_children(self, cursor: QTextCursor, node: HtmlNode):
        for child in node.children:
            self._render_node(cursor, child)

    def _new_line(self, cursor: QTextCursor):
        # The first _new_line called shouldn't add another block
        # Therefore this guard is necessary
        if self.at_beginning:
            self.at_beginning = False
            return

        # Add new block
        cursor.insertBlock()

        # Reset indent
        self.indent = 0
        self.block_fmt = QTextBlockFormat(default_block_format)

        # Reset char format (now with default font size)
        self.char_fmt = QTextCharFormat(default_char_format)
        cursor.setCharFormat(self.char_fmt)

    def _end_line(self, cursor: QTextCursor):
        # Set block format with indent and heading level before adding new block
        list_indent = max(0, self.nested_ul_tags - 1)
        self.block_fmt.setIndent(self.indent + list_indent)
        cursor.setBlockFormat(self.block_fmt)

    def _apply_block_format_styles(self, style):
        # Define aliases
        BlockProperty = QTextBlockFormat.Property
        LineHeightType = QTextBlockFormat.LineHeightTypes
        ProportionalHeight = LineHeightType.ProportionalHeight.value
        FixedHeight = LineHeightType.FixedHeight.value

        # Left margin for blocks
        if 'left-margin' in style:
            """
            Parse a left-margin string (e.g., "10px", "-1.5em", "10") and return a pixel value.
            If the unit is "em", multiply the numeric value by default_font_size.
            If there's no unit or the unit is "px", return the value as a float.
            """
            m = re.match(r'(-?[\d.]+)\s*(px|em)?', style['left-margin'])
            if m:
                value = float(m.group(1))
                unit = m.group(2)
                if unit == 'em':
                    self.block_fmt.setProperty(QTextFormat.Property.BlockLeftMargin, value * default_font_pointsize)
                else:
                    # Treat no unit or 'px' as pixels.
                    self.block_fmt.setProperty(QTextFormat.Property.BlockLeftMargin, value)
            else:
                raise ValueError('Unable to parse left-margin property')

        # Qt block indent
        if '-qt-block-indent' in style:
            # Extract numeric value from the -qt-block-indent string.
            m = re.match(r'(\d+)', style['-qt-block-indent'].strip())
            if m:
                self.indent = int(m.group(1))
            else:
                raise ValueError('Unable to parse -qt-block-indent property')

        # Line height
        if 'line-height' in style:
            line_height_str = style['line-height'].strip()
            match = re.match(r'([\d.]+)\s*(%)?', line_height_str)
            if match:
                value = float(match.group(1))
                if match.group(2) == '%':
                    self.block_fmt.setProperty(BlockProperty.LineHeightType, ProportionalHeight)
                    self.block_fmt.setProperty(BlockProperty.LineHeight, value)
                else:
                    self.block_fmt.setProperty(BlockProperty.LineHeightType, FixedHeight)
                    self.block_fmt.setProperty(BlockProperty.LineHeight, value)
            elif line_height_str == 'normal':
                self.block_fmt.setProperty(BlockProperty.LineHeightType, default_block_format.lineHeightType)
                self.block_fmt.setProperty(BlockProperty.LineHeight, default_block_format.lineHeight())
            elif line_height_str == 'unset':
                self.block_fmt.clearProperty(BlockProperty.LineHeightType)
                self.block_fmt.clearProperty(BlockProperty.LineHeight)
            else:
                raise ValueError('Unable to parse line-height property')

    # -----------------------------------------------
    # 3. Tokenize and parse
    # -----------------------------------------------

    @staticmethod
    def _tokenize(html_input: str):
        Type = Token.Type

        for match in TAG_PATTERN.finditer(html_input):
            tag = match.group("tag")
            text = match.group("text")

            if text:
                if text.strip('\n') == "":
                    continue
                yield Token(type=Type.text, content=html.unescape(text))
            elif tag:
                if tag.startswith("</"):
                    # End tag
                    tagname = tag[2:-1].strip().lower()
                    yield Token(type=Type.end_tag, name=tagname)
                else:
                    is_self_closing = tag.endswith("/>")
                    tag_content = tag[1:-2].strip() if is_self_closing else tag[1:-1].strip()

                    parts = tag_content.split(None, 1)
                    tagname = parts[0].lower()
                    attr_string = parts[1] if len(parts) > 1 else ""

                    attrs = {
                        m.group("name").lower(): m.group("value")
                        for m in ATTR_PATTERN.finditer(attr_string)
                    }

                    yield Token(
                        type = Type.self_closing_tag if is_self_closing or tagname in SELF_CLOSING_TAGS else Type.start_tag,
                        name = tagname,
                        attrs = attrs or None
                    )

    @staticmethod
    def _parse(tokens) -> List[HtmlNode]:
        pos = 0

        def parse_nodes(stop_tag: Optional[str] = None) -> List[HtmlNode]:
            nonlocal pos
            nodes = []

            while pos < len(tokens):
                token = tokens[pos]

                if token.type == Token.Type.text:
                    nodes.append(HtmlNode(type=HtmlNode.Type.text, content=token.content))
                    pos += 1

                elif token.type == Token.Type.start_tag:
                    pos += 1
                    children = parse_nodes(stop_tag=token.name)
                    nodes.append(HtmlNode(
                        type=HtmlNode.Type.element,
                        name=token.name,
                        attrs=token.attrs or {},
                        children=children
                    ))

                elif token.type == Token.Type.self_closing_tag:
                    nodes.append(HtmlNode(
                        type=HtmlNode.Type.element,
                        name=token.name,
                        attrs=token.attrs or {},
                        children=[]
                    ))
                    pos += 1

                elif token.type == Token.Type.end_tag:
                    if stop_tag and token.name == stop_tag:
                        pos += 1
                        break
                    else:
                        # Unexpected closing tag — ignore or warn
                        pos += 1

            return nodes

        return parse_nodes()

    # -----------------------------------------------
    # 4. Extract styles from HTML head
    # -----------------------------------------------

    def _extract_context(self, ast: HtmlNode) -> None:
        # Assuming ast represents the <head> element,
        # iterate over its children.
        for child in ast.children:
            if child.name == 'style':
                for style_child in child.children:
                    style_text = style_child.content or ""
                    self.context.styles.update(HtmlImporter._parse_css_rules(style_text))

            elif child.name == 'meta':
                attrs = child.attrs
                if 'name' in attrs and 'content' in attrs:
                    self.context.metadata[attrs['name']] = attrs['content']

    @staticmethod
    def _parse_css_rules(css_text: str) -> dict:
        """
        Parses a simple CSS string and returns a dictionary mapping individual selectors
        to their respective property dictionaries.

        Example:
            Input:
                "p { margin-top: 10px; color: red; } h1 { font-size: 20pt; }"
            Output:
                {
                    "p": {"margin-top": "10px", "color": "red"},
                    "h1": {"font-size": "20pt"}
                }

        Handles grouped selectors like:
            "p, li { margin-left: 0px; }"
        correctly as:
            {
                "p": {"margin-left": "0px"},
                "li": {"margin-left": "0px"}
            }
        """
        rules = {}

        # Match selectors + property blocks
        rule_pattern = re.compile(r'([^{]+)\{([^}]+)\}')

        for match in rule_pattern.finditer(css_text):
            selector_block = match.group(1)
            properties_str = match.group(2).strip()

            # Parse the property declarations
            properties = parse_properties(properties_str)

            # Support multiple selectors separated by commas
            selectors = [s.strip() for s in selector_block.split(',')]
            for selector in selectors:
                if selector in rules:
                    rules[selector].update(properties)
                else:
                    rules[selector] = dict(properties)  # Make a copy

        return rules

    # -----------------------------------------------
    # 5. Find node
    # -----------------------------------------------

    @staticmethod
    def _find_node(root, tag_name: str):
        """
        Recursively searches for a node with the given tag name in the AST.

        Parameters:
            root (HtmlNode or List[HtmlNode]): The root of the AST or a list of nodes.
            tag_name (str): The tag name to search for (case-insensitive).

        Returns:
            HtmlNode or None: The first node matching the tag name, or None if not found.
        """

        # If the root is a list, iterate over it and search each node.
        if isinstance(root, list):
            for node in root:
                result = HtmlImporter._find_node(node, tag_name)
                if result is not None:
                    return result
            return None

        # Use alias for convenience
        root_node: HtmlNode = root

        # Check if the current node matches the tag (case-insensitive).
        if root_node.name and root_node.name.lower() == tag_name.lower():
            return root_node

        # Otherwise, search recursively in the children.
        for child in root_node.children:
            result = HtmlImporter._find_node(child, tag_name)
            if result is not None:
                return result

        return None
