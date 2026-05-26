from dataclasses import dataclass

from PyQt6.QtGui import (QTextBlock, QTextFragment, QTextCharFormat)

from notetree.texteditor.style import *

@dataclass
class Format:
    class Type(int):
        # This is used as a precedence list
        bold = 0
        italic = 1
        underline = 2
        pointsize = 3
        link = 4

    type: Type
    start: int
    end: int = -1
    attrs: dict | None = None

@dataclass
class FormatChange:
    type: Format.Type
    attrs: dict | None = None
    open: bool = True

@dataclass
class ExportableFragment:
    fragment: QTextFragment
    # The format changes are ordered in a such a manner
    # that the inner/outer always match when you apply them
    # in the given order
    fmt_changes: list[FormatChange] | None = None

class InlineFormatResolver:
    """
    InlineFormatResolver is a helper class to export a QTextBlock into HTML and Markdown.
    It organizes the nested char formats in the fragments such that the inner/outer tags
    don't conflict. For instance, we want to avoid output like this:

        <strong><em>This is an </strong>example</em>

    The problem here is that the inner/outer tags do not match. A lookahead is required
    to get the output right.
    Therefore, InlineFormatResolver organizes the format differences between fragments such
    that it's clear which format has to be the outer and which one the inner.
    If both cases are equally possible, there is a precedence list which one takes priority.
    """
    def __init__(self, block: QTextBlock, start: int = -1, end: int = -1):
        self.block = block

        # Initialize standard char format
        global default_char_format, default_font_pointsize
        if not default_char_format:
            default_char_format = init_default_char_format()
            default_font_pointsize = init_default_font_pointsize()

        # Start and end position in number of characters relative to document start
        self._start = start
        self._end = end

        # Shall the formats for whole block be resolved or just a range?
        self._use_range = start != -1 and end != -1

        # The following indexes relate the the start and end positions
        # They refer to the fragment indexes within the block
        self._first_index = -1
        self._last_index = -1

        # Initialize lists to be used as output
        self._formats: list[Format] = []
        self.fragments: list[ExportableFragment] = []

        if self._use_range:
            self._normalize_boundaries()
        # Extract all format changes within this block
        self._detect_format_changes()
        if self._use_range:
            # Remove format changes that are not within the given range
            self._clean_up()
        # Set up the format changes to be in the right order
        self._resolve_change_stack()

    def _resolve_change_stack(self):
        if not self.fragments:
            return

        open_stack: list[Format] = []

        # Set first and last index for iteration
        if not self._use_range:
            self._first_index = 0
            self._last_index = len(self.fragments) - 1

        for index in range(self._first_index, self._last_index + 1):
            # Resolve format changes for the current fragment
            fragment = self.fragments[index - self._first_index]
            fmt_changes = fragment.fmt_changes  # is empty so far

            # Open formats at the beginning of the fragment
            open_fmts: list[Format] = sorted([f for f in self._formats if f.start == index],
                                             key=lambda f: (f.start, -f.end, f.type))

            # Add all opening formats
            for open_fmt in open_fmts:
                fmt_changes.append(FormatChange(open_fmt.type, open_fmt.attrs, True))
                open_stack.append(open_fmt)

            # Close formats at the end of the fragment
            close_fmts: list[Format] = sorted([f for f in self._formats if f.end == index],
                                              key=lambda f: (f.start, f.type))

            # Iterate through closing stack and append all closing formats
            while close_fmts:
                close_fmt = close_fmts.pop()
                last_open_fmt = open_stack.pop()
                # Does the next closing format match the last opened format?
                while last_open_fmt.type != close_fmt.type:
                    # If they don't match, close the last opened format
                    fmt_changes.append(FormatChange(last_open_fmt.type, last_open_fmt.attrs, open=False))
                    if last_open_fmt.end > index:
                        # Update start index of last opened format
                        # Thus, it will be re-opened in the next iteration
                        last_open_fmt.start = index + 1
                    last_open_fmt = open_stack.pop()
                fmt_changes.append(FormatChange(close_fmt.type, close_fmt.attrs, open=False))

    def _clean_up(self):
        updated = []
        for fmt in self._formats:
            if fmt.start <= self._last_index and fmt.end >= self._first_index:
                if fmt.start < self._first_index:
                    fmt.start = self._first_index
                if fmt.end > self._last_index:
                    fmt.end = self._last_index
                updated.append(fmt)
        self._formats = updated

    def _detect_format_changes(self):
        Type = Format.Type

        prev_fragment = QTextFragment()
        it = self.block.begin()
        index = 0
        while not it.atEnd():
            # Char format from previous fragment
            if prev_fragment.isValid():
                prev_fmt = prev_fragment.charFormat()
            else:
                prev_fmt = QTextCharFormat(default_char_format)

            # Char format from current fragment
            fragment = it.fragment()
            if not fragment.isValid():
                break
            else:
                cur_fmt = fragment.charFormat()

            # Char format from next fragment
            it += 1
            if not it.atEnd():
                next_fragment = it.fragment()
                if next_fragment.isValid():
                    next_fmt = next_fragment.charFormat()
                else:
                    next_fmt = QTextCharFormat(default_char_format)
            else:
                next_fmt = QTextCharFormat(default_char_format)

            # Determine if fragment is within boundaries
            if self._use_range:
                if self._start < fragment.position() + fragment.length() and self._end > fragment.position():
                    if self._first_index == -1:
                        self._first_index = index
                    self._last_index = index
                    within_boundaries = True
                else:
                    within_boundaries = False
            else:
                within_boundaries = True

            # Add fragment to list if that's the case
            if within_boundaries:
                self.fragments.append(ExportableFragment(fragment, []))

            # Detect all format changes
            # Handle opening tags
            if not is_markdown_strong(prev_fmt) and is_markdown_strong(cur_fmt):
                self._formats.append(Format(Type.bold, index))
            if not prev_fmt.font().italic() and cur_fmt.font().italic():
                self._formats.append(Format(Type.italic, index))
            if not prev_fmt.font().underline() and cur_fmt.font().underline():
                self._formats.append(Format(Type.underline, index))
            if prev_fmt.font().pointSize() != cur_fmt.font().pointSize() and cur_fmt.font().pointSize() != default_font_pointsize:
                self._formats.append(Format(Type.pointsize, index, attrs={'font-size': str(int(cur_fmt.font().pointSize()))}))
            if not prev_fmt.isAnchor() and cur_fmt.isAnchor():
                self._formats.append(Format(Type.link, index, attrs={'href': cur_fmt.anchorHref()}))
            elif prev_fmt.isAnchor() and cur_fmt.isAnchor() and prev_fmt.anchorHref() != cur_fmt.anchorHref():
                self._formats.append(Format(Type.link, index, attrs={'href': cur_fmt.anchorHref()}))

            # Handle closing tags
            if is_markdown_strong(cur_fmt) and not is_markdown_strong(next_fmt):
                self._last_of_type(Type.bold).end = index
            if cur_fmt.font().italic() and not next_fmt.font().italic():
                self._last_of_type(Type.italic).end = index
            if cur_fmt.font().underline() and not next_fmt.font().underline():
                self._last_of_type(Type.underline).end = index
            if cur_fmt.font().pointSize() != next_fmt.font().pointSize() and cur_fmt.font().pointSize() != default_font_pointsize:
                self._last_of_type(Type.pointsize).end = index
            if cur_fmt.isAnchor() and not next_fmt.isAnchor():
                self._last_of_type(Type.link).end = index
            elif cur_fmt.isAnchor() and next_fmt.isAnchor() and cur_fmt.anchorHref() != next_fmt.anchorHref():
                self._last_of_type(Type.link).end = index

            prev_fragment = fragment
            index += 1

    def _last_of_type(self, type: Format.Type) -> Format | None:
        length = len(self._formats)
        for i in reversed(range(length)):
            f: Format = self._formats[i]
            if f.type == type and f.end == -1:
                return f
        return None

    def _normalize_boundaries(self):
        # Define aliases
        block_start = self.block.position()
        block_end = self.block.position() + self.block.length()

        # Set the boundaries such that they won't exceed the blocks boundaries
        self._start = max(self._start, block_start)
        self._end = min(self._end, block_end)
        if self._start == block_start and self._end == block_end:
            # Deactivate range check, because it's unnecessary
            self._use_range = False
