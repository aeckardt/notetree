import re
import sys

from PyQt6.QtGui import (QTextCharFormat, QFont)

def apply_html_style(style: dict, char_fmt: QTextCharFormat) -> bool:
    fmt_changed = False

    # Font size
    if 'font-size' in style:
        # Extract numeric value from the font-size string.
        font_size_raw = style['font-size']
        m = re.match(r'(\d+)', font_size_raw)
        if m:
            char_fmt.setFontPointSize(int(m.group(1)))
            fmt_changed = True
        else:
            # Named sizes fallback
            named_sizes = {
                'xx-small': 8,
                'x-small': 9,
                'small': 10,
                'medium': 12,
                'large': 14,
                'x-large': 16,
                'xx-large': 18,
            }
            point_size = named_sizes.get(font_size_raw.lower())
            if point_size:
                char_fmt.setFontPointSize(point_size)
                fmt_changed = True
            else:
                # Graceful fallback: ignore unknown sizes
                print(f"Warning: Unsupported font-size '{font_size_raw}' ignored.", file=sys.stderr)

    # Font weight
    if 'font-weight' in style:
        weight_raw = style['font-weight'].lower()
        weight_map = {
            'normal': QFont.Weight.Normal,
            'bold': QFont.Weight.Bold,
            'bolder': QFont.Weight.Bold,
            'lighter': QFont.Weight.Light,
            '100': QFont.Weight.Thin,
            '200': QFont.Weight.ExtraLight,
            '300': QFont.Weight.Light,
            '400': QFont.Weight.Normal,
            '500': QFont.Weight.Medium,
            '600': QFont.Weight.DemiBold,
            '700': QFont.Weight.Bold,
            '800': QFont.Weight.ExtraBold,
            '900': QFont.Weight.Black,
        }
        qweight = weight_map.get(weight_raw)
        if qweight is not None:
            char_fmt.setFontWeight(qweight)
            fmt_changed = True
        else:
            print(f"Warning: Unsupported font-weight '{weight_raw}' ignored.", file=sys.stderr)

    # Font style (italic or not)
    if 'font-style' in style:
        style_raw = style['font-style'].lower()
        if style_raw in ('italic', 'oblique'):
            char_fmt.setFontItalic(True)
            fmt_changed = True
        elif style_raw == 'normal':
            char_fmt.setFontItalic(False)
            fmt_changed = True
        else:
            print(f"Warning: Unsupported font-style '{style_raw}' ignored.", file=sys.stderr)

    # Text Decoration (underline or not)
    if 'text-decoration' in style:
        decoration = style['text-decoration'].lower()
        if decoration == 'underline':
            char_fmt.setFontUnderline(True)
            fmt_changed = True
        elif 'none' in decoration:
            char_fmt.setFontUnderline(False)
            fmt_changed = True
        else:
            print(f"Warning: Unsupported text-decoration '{decoration}' ignored.", file=sys.stderr)

    # Other styles are currently not supported

    # Returns if any changes have been made to char_fmt
    return fmt_changed

def parse_properties(properties_str: str) -> dict:
    properties = {}
    for prop in properties_str.split(';'):
        prop = prop.strip()
        if not prop or ':' not in prop:
            continue
        name, value = prop.split(':', 1)
        properties[name.strip()] = value.strip()
    return properties