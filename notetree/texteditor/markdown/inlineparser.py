from dataclasses import dataclass
from typing import Optional, List, Union
from enum import IntEnum
import unicodedata
import re
import html
import urllib.parse

@dataclass
class InlineNode:
    class Type(IntEnum):
        container = 0
        strong = 1
        emph = 2
        inline_link = 3
        image = 4
        html_tag = 5
        text = 6
    type: Type
    content: Optional[str] = None  # Contains text or HTML tag name
    attrs: Optional[dict] = None
    children: Optional[List["InlineNode"]] = None

@dataclass
class DelimiterRun:
    """
    A "run" of delimiters.
    E.g. *** is a sequence of delimiter characters treated as one unit.
        An * is a delimiter.
        An ** is a delimiter run of length 2.
        An *** is a delimiter run of length 3.
    The content field contains the literal delimiter text.
    """
    content: str  # e.g. '*', '**', '***', '!['

@dataclass
class InlineHtmlTag:
    content: str  # Original input string for the tag
    tag: str  # 'ins', 'span', ...
    attrs: Optional[dict] = None

@dataclass
class ScopeMarker:
    """
    Every open instance of ScopeMarker contains structure in form of a
    floating node. This is wrapped by a closing ScopeMarker and then integrated
    into the tree. Alternatively, the marker will be disregarded as text.
    """
    class Type(IntEnum):
        # The enum integers are their priority
        # Lower integer = higher binding priority when resolving the stack
        html_tag = 0  # '<ins>', <span>, ...
        bracket = 1   # '![', '[' or ']'
        asterisk = 2  # '*', '**', '***', ...
    type: Type
    marker: Optional[Union[DelimiterRun, InlineHtmlTag]] = None
    can_open: bool = False
    can_close: bool = False
    node: Optional[InlineNode] = None

def is_punctuation(ch: Optional[str]) -> bool:
    if ch is None:
        return False
    # Unicode categories starting with 'P' are all punctuation
    return unicodedata.category(ch).startswith('P')

class MarkdownInlineParser:
    def __init__(self, line_input: str = ''):
        self.input = line_input

        # Parse the line with a one-pass Markdown parser
        if self.input:
            self.parse()
        else:
            self.ast_root = InlineNode(InlineNode.Type.container, children=[])

    def parse(self):
        MarkerType = ScopeMarker.Type
        NodeType = InlineNode.Type

        self.ast_root = InlineNode(NodeType.container, children=[])
        self.current_parent = self.ast_root
        self.open_scope_stack: list[ScopeMarker] = []

        self.pos = 0
        self.length = len(self.input)
        self.text = ''

        while self.pos < self.length:
            ch = self.input[self.pos]
            match ch:
                case '*':
                    self.flush_text()

                    # Count the asterisks
                    count = 1
                    while self.pos + count < self.length and self.input[self.pos+count] == '*':
                        count += 1

                    # Character just before the run
                    prev_char = self.input[self.pos-1] if self.pos > 0 else None
                    # Character just after the run
                    next_char = self.input[self.pos+count] if self.pos+count < self.length else None

                    prev_is_ws = prev_char.isspace() if prev_char else True
                    prev_is_p  = is_punctuation(prev_char)
                    prev_is_tc = prev_char == '>'
                    next_is_ws = next_char.isspace() if next_char else True
                    next_is_p  = is_punctuation(next_char)
                    next_is_to = next_char == '<'

                    # A run is left-flanking if:
                    #  1) next_char is not whitespace, AND
                    #  2) (next_char is not punctuation OR prev_char is whitespace or punctuation)
                    left_flanking = (not next_is_ws) and (not next_is_p or prev_is_ws or prev_is_p or prev_is_tc)

                    # A run is right-flanking if:
                    #  1) prev_char is not whitespace, AND
                    #  2) (prev_char is not punctuation OR next_char is whitespace or punctuation)
                    right_flanking = (not prev_is_ws) and (not prev_is_p or next_is_ws or next_is_p or next_is_to)

                    marker = ScopeMarker(MarkerType.asterisk, DelimiterRun('*' * count), left_flanking, right_flanking)
                    if right_flanking:
                        # Get matching marker node from stack
                        open_marker = self.find_opening_marker(marker)
                        if open_marker:
                            # Resolve the two markers (left and right side may have different length)
                            self.consume_match(open_marker, marker)
                        elif left_flanking:
                            self.push_scope_marker(marker)
                        else:
                            # The marker could not be matched
                            # Will be added as text...
                            self.integrate_marker_as_text(marker)
                    elif left_flanking:
                        self.push_scope_marker(marker)
                    else:
                        self.integrate_marker_as_text(marker)

                    # Advance past the asterisks
                    self.pos += count

                case '!':
                    if self.pos + 1 < self.length and self.input[self.pos + 1] == '[':
                        # '![' found at pos => push ScopeMarker to stack
                        self.flush_text()
                        marker = ScopeMarker(MarkerType.bracket, DelimiterRun('!['), True, False)
                        self.push_scope_marker(marker)
                        self.pos += 2
                    else:
                        # Disregard as text
                        self.text += ch
                        self.pos += 1

                case '[':
                    self.flush_text()
                    marker = ScopeMarker(MarkerType.bracket, DelimiterRun(ch), True, False)
                    self.push_scope_marker(marker)
                    self.pos += 1
                case ']':
                    self.flush_text()
                    marker = ScopeMarker(MarkerType.bracket, DelimiterRun(ch), False, True)
                    self.pos += 1

                    # Get matching marker node from stack
                    open_marker = self.find_opening_marker(marker)
                    if open_marker is None:
                        # No match found, add ']' as text
                        self.integrate_marker_as_text(marker)
                        continue
                    # Check if next char is opening parenthesis
                    if self.pos >= self.length or self.input[self.pos] != '(':
                        self.integrate_marker_as_text(open_marker)
                        self.integrate_marker_as_text(marker)
                        continue

                    # Look ahead to find closing parenthesis
                    fwdpos = self.pos + 1
                    res_path = ''
                    while fwdpos < self.length:
                        ch = self.input[fwdpos]
                        if ch in '()':
                            break
                        res_path += ch
                        fwdpos += 1
                    res_path = res_path.strip()
                    if ch == '(' or re.search(r'\s', res_path):
                        # Condition for valid link / image syntax violated!
                        self.integrate_marker_as_text(open_marker)
                        self.integrate_marker_as_text(marker)
                        continue
                    else:
                        res_path = urllib.parse.unquote(res_path)

                    # Valid link / image syntax found!
                    node = open_marker.node
                    if open_marker.marker.content == '![':
                        node.attrs = {'src': res_path}
                        node.type = NodeType.image
                    else:
                        node.attrs = {'href': res_path}
                        node.type = NodeType.inline_link

                    # Integrate node into tree
                    self.integrate_node(node)

                    # Advance to after the closing parenthesis
                    self.pos = fwdpos + 1

                case '<':
                    self.flush_text()
                    # Parse HTML separately
                    marker = self.try_parse_html_tag()
                    if not marker:
                        self.text += '<'
                        self.pos += 1
                        continue
                    if marker.can_open:
                        self.push_scope_marker(marker)
                    elif marker.can_close:
                        open_marker = self.find_opening_marker(marker)
                        if not open_marker:
                            self.integrate_marker_as_text(marker)
                            continue
                        open_marker.node.type = NodeType.html_tag
                        open_marker.node.content = open_marker.marker.tag
                        open_marker.node.attrs = open_marker.marker.attrs
                        self.integrate_node(open_marker.node)
                    elif not marker.can_open and not marker.can_close:
                        marker.node.type = NodeType.html_tag
                        marker.node.content = marker.marker.tag
                        marker.node.attrs = marker.marker.attrs
                        self.integrate_node(marker.node)

                case _:
                    self.text += ch
                    self.pos += 1

        # Clean up and append unclosed markers as text
        self.flush_text()
        while self.open_scope_stack:
            marker = self.pop_scope_marker()
            self.integrate_marker_as_text(marker)

    def find_opening_marker(self, marker: ScopeMarker) -> Optional[ScopeMarker]:
        length = len(self.open_scope_stack)

        # Find the nearest position of the marker in the stack
        index = length - 1
        while index >= 0:
            open_marker = self.open_scope_stack[index]
            if open_marker.type == marker.type:
                if marker.type == ScopeMarker.Type.html_tag:
                    open_tag = open_marker.marker.tag
                    close_tag = marker.marker.tag
                    if open_tag == close_tag:
                        break
                else:
                    break
            elif open_marker.type < marker.type:
                # The open scope in the stack has higher priority
                # Therefore, no match is possible
                return None
            index -= 1
        if index == -1:
            return None

        # Reduce the stack until the top element matches the marker
        while True:
            popped_marker = self.pop_scope_marker()
            if popped_marker.type == marker.type:
                if marker.type == ScopeMarker.Type.html_tag:
                    popped_tag = popped_marker.marker.tag
                    close_tag = marker.marker.tag
                    if popped_tag == close_tag:
                        return popped_marker
                else:
                    return popped_marker
            # Interpret un-matched markers as text
            self.integrate_marker_as_text(popped_marker)

    def consume_match(self, left_marker: ScopeMarker, right_marker: ScopeMarker):
        # Marker types are assumed to be asterisk, when calling this function
        left_length = len(left_marker.marker.content)
        right_length = len(right_marker.marker.content)
        if left_length == right_length:
            # Append matched marker node to higher node
            self.finalize_emphasis_marker(left_marker)
            self.integrate_node(left_marker.node)
        elif left_length > right_length:
            # Split node: Move the structure from the left side to the right side
            # and then add the right side marker as child to the left side

            # First, create a node for the right side marker and finalize it
            right_marker.node = InlineNode(InlineNode.Type.container, children=left_marker.node.children)
            self.finalize_emphasis_marker(right_marker)

            # Second, make the right side node a child of the left side node
            left_marker.node.children = [right_marker.node]

            # Reduce open number of asterisks on left side
            left_marker.marker.content = '*' * (left_length - right_length)

            # Put the left marker back on the stack
            self.push_scope_marker(left_marker)
        else:  # left_length < right_length
            # Integrate matched marker node to the tree
            self.finalize_emphasis_marker(left_marker)
            self.integrate_node(left_marker.node)

            # Update marker to match left_length chars
            right_marker.marker.content = '*' * (right_length - left_length)

            # Try to match asterisks to the left with the altered stack
            open_marker = self.find_opening_marker(right_marker)
            if open_marker is None:
                self.push_scope_marker(right_marker)
                return
            self.consume_match(open_marker, right_marker)

    def finalize_emphasis_marker(self, marker: ScopeMarker):
        NodeType = InlineNode.Type
        count = len(marker.marker.content)
        node = marker.node
        if count % 2 == 1:
            if count > 1:
                node.type = NodeType.strong
                sub_node = InlineNode(NodeType.emph, children=node.children)
                node.children = [sub_node]
            else:
                node.type = NodeType.emph
        else:
            node.type = NodeType.strong

    def try_parse_html_tag(self) -> Optional[ScopeMarker]:
        Type = ScopeMarker.Type

        # Condition for entering this method:
        # At self.pos there is a '<'.
        fwd_pos = self.pos + 1  # Advancing past '<'
        if fwd_pos >= self.length:
            return None

        def read_identifier() -> str:
            nonlocal fwd_pos
            # Read name
            identifier = self.input[fwd_pos]
            # The identifier needs to start with an alphabetic character
            if not identifier.isalpha():
                return ''
            fwd_pos += 1
            while fwd_pos < self.length and (self.input[fwd_pos].isalnum() or self.input[fwd_pos] in ['-_:']):
                identifier += self.input[fwd_pos]
                fwd_pos += 1
            if fwd_pos >= self.length:
                # If the end of the input has been reached, there is no valid HTML tag
                # Therefore return empty string
                return ''
            return identifier

        def skip_whitespaces():
            nonlocal fwd_pos
            while fwd_pos < self.length and self.input[fwd_pos].isspace():
                fwd_pos += 1

        def read_attribute_value():
            nonlocal fwd_pos
            value = ''
            while fwd_pos < self.length:
                if self.input[fwd_pos].isalnum() or self.input[fwd_pos] in '-_.:&;,':
                    value += self.input[fwd_pos]
                    fwd_pos += 1
                else:
                    return value
            return None

        # Look for optional closing slash
        closing_tag = self.input[fwd_pos] == '/'
        if closing_tag:
            fwd_pos += 1
        if fwd_pos >= self.length:
            return None

        # Read tag name
        # Note: Whitespaces before the tag name are not allowed
        tag_name = read_identifier()
        if not tag_name:
            return None

        # Consume whitespaces
        skip_whitespaces()
        if fwd_pos >= self.length:
            # Return if the input has ended unexpectedly
            return None

        # If the tag is also closing tag, check for '>'
        if closing_tag:
            if self.input[fwd_pos] == '>':
                # Valid closing tag found!
                # Advance position for parser
                content = self.input[self.pos:fwd_pos+1]
                self.pos = fwd_pos + 1
                return ScopeMarker(Type.html_tag, InlineHtmlTag(content, tag_name), False, True)
            else:
                # Condition for valid closing tag violated
                # '>' expected, but not found
                return None

        # Parse attributes or end of tag
        attrs = None
        while fwd_pos < self.length:
            ch = self.input[fwd_pos]
            if ch.isspace():
                fwd_pos += 1
            elif ch.isalpha():
                # Parse attribute
                # Read attribute name
                attr_name = read_identifier()
                if not attr_name:
                    return None

                # Consume whitespaces
                skip_whitespaces()
                if fwd_pos >= self.length:
                    return None

                # Check for equality sign
                if self.input[fwd_pos] == '=':
                    fwd_pos += 1

                    # Consume whitespaces
                    skip_whitespaces()
                    if fwd_pos >= self.length:
                        return None

                    # Check for quotation marks
                    ch = self.input[fwd_pos]
                    if ch in '"\'':
                        quot_type = ch
                        fwd_pos += 1
                        value = ''
                        while fwd_pos < self.length and self.input[fwd_pos] != quot_type:
                            value += self.input[fwd_pos]
                            fwd_pos += 1
                        if fwd_pos >= self.length:
                            return None
                        fwd_pos += 1
                    else:
                        value = read_attribute_value()

                    if not value:
                        return None

                    attr_value = html.unescape(value.strip())

                else:
                    attr_value = True

                if not attrs:
                    attrs = {}
                attrs[attr_name] = attr_value

            elif ch == '/':
                # Self closing tag
                if fwd_pos + 1 < self.length and self.input[fwd_pos+1] == '>':
                    # Valid self closing tag found!
                    content = self.input[self.pos:fwd_pos+2]
                    self.pos = fwd_pos + 2
                    return ScopeMarker(Type.html_tag, InlineHtmlTag(content, tag_name, attrs), False, False)
            elif ch == '>':
                # Closing tag found
                content = self.input[self.pos:fwd_pos+1]
                self.pos = fwd_pos + 1
                return ScopeMarker(Type.html_tag, InlineHtmlTag(content, tag_name, attrs), True, False)
            else:
                # Other characters are not allowed here:
                return None

        return None

    def push_scope_marker(self, marker: ScopeMarker):
        if marker.node is None:
            # Create a node for an opening marker
            # It's temporarily a floating node which can have children
            # Later it will either
            # - be integrated into the tree or 
            # - it will be flattened and the marker will be treated as text
            marker.node = InlineNode(InlineNode.Type.container, children=[])
        self.current_parent = marker.node

        # Push marker to the stack
        self.open_scope_stack.append(marker)

    def pop_scope_marker(self) -> ScopeMarker:
        popped = self.open_scope_stack.pop()
        # Update current parent
        if self.open_scope_stack:
            self.current_parent = self.open_scope_stack[-1].node
        else:
            self.current_parent = self.ast_root
        return popped

    def integrate_node(self, node: InlineNode):
        # Append the text node to the current parent node
        self.current_parent.children.append(node)

    def integrate_marker_as_text(self, marker: ScopeMarker):
        # Append text node with marker characters to the tree
        self.integrate_node(InlineNode(InlineNode.Type.text, content=marker.marker.content))

        if marker.node:
            # Flatten the structure by adding all the children from the floating
            # marker node to the current parent node
            self.current_parent.children += marker.node.children

            # The inline node from parsing is not needed anymore
            marker.node = None

    def flush_text(self):
        if self.text:
            # Append new text node to the tree
            self.integrate_node(InlineNode(InlineNode.Type.text, content=self.text))

            # Clear text
            self.text = ''
