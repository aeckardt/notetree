from notetree.texteditor.html.exporter import HtmlExporter
from notetree.texteditor.markdown.importer import MarkdownImporter

def test_markdown_importer():
    test_cases = [
        {
            "input": """***bold and italic* still open**""",
            "expected_html": "<strong><em>bold and italic</em> still open</strong>"
        },
        {
            "input": "*italic with **mismatch* bold**",
            "expected_html": "<em>italic with mismatch bold</em>"
        },
        {
            "input": "*x* **y**",
            "expected_html": "<em>x</em> <strong>y</strong>"
        },
        {
            "input": "*x **y***",
            "expected_html": "<em>x <strong>y</strong></em>"
        },
        {
            "input": "*x **y** z*",
            "expected_html": "<em>x <strong>y</strong> z</em>"
        },
        {
            "input": "***x y***",
            "expected_html": "<strong><em>x y</em></strong>"
        },
        {
            "input": "***x y* z**",
            "expected_html": "<strong><em>x y</em> z</strong>"
        },
        {
            "input": "***x y** z*",
            "expected_html": "<em><strong>x y</strong> z</em>"
        },
        {
            "input": "**x *y***",
            "expected_html": "<strong>x <em>y</em></strong>"
        },
        {
            "input": "**x *y* z**",
            "expected_html": "<strong>x <em>y</em> z</strong>"
        },
        {
            "input": "**bold *and italic* inside**",
            "expected_html": "<strong>bold <em>and italic</em> inside</strong>"
        },
        {
            "input": "*italic **and bold** inside*",
            "expected_html": "<em>italic <strong>and bold</strong> inside</em>"
        },
        {
            "input": "*unclosed italic",
            "expected_html": "*unclosed italic"  # fallback to plain text
        },
        {
            "input": "**unclosed bold",
            "expected_html": "**unclosed bold"
        },
        {
            "input": "***bold and italic***",
            "expected_html": "<strong><em>bold and italic</em></strong>"
        },
        {
            "input": "*[*unmatched italic](https://google.com)",
            "expected_html": "*<a href=\"https://google.com\">*unmatched italic</a>"
        },
        {
            "input": "*[*broken italic link*](https://googl)",
            "expected_html": "*<em><a href=\"https://googl\">broken italic link</a></em>"
        },
        {
            "input": "[This is not a link](because of the whitespace)",
            "expected_html": "[This is not a link](because of the whitespace)"
        },
        {
            "input": "[This is not a valid link]((because_of_double_parentheses))",
            "expected_html": "[This is not a valid link]((because_of_double_parentheses))"
        },
        {
            "input": "[This is a valid link](  however  )",
            "expected_html": "<a href=\"however\">This is a valid link</a>"
        },
        {
            "input": "<span style=\"font-size:15pt\"><ins>This is an HTML</ins></span> test.",
            "expected_html": "<ins><span style=\"font-size:15pt\">This is an HTML</span></ins> test.",
        },
        {
            "input": "This <- is not meant to be interpreted as HTML. And -> this neither.",
            "expected_html": "This &lt;- is not meant to be interpreted as HTML. And -&gt; this neither.",
        },
        {
            "input": "> The blockquote feature is not implemented yet.",
            "expected_html": "&gt; The blockquote feature is not implemented yet.",
        },
        {
            "input": "Non-<ins><strong>matching HTML</ins></strong> tags.",
            "expected_html": "Non-<ins>&lt;strong&gt;matching HTML</ins>&lt;/strong&gt; tags.",
        },
        {
            "input": "<ins>Overlapping **</ins>styles not resolved**",
            "expected_html": "<ins>Overlapping **</ins>styles not resolved**",
        },
        {
            "input": "**<ins>Composite styles resolved</ins>**",
            "expected_html": "<strong><ins>Composite styles resolved</ins></strong>",
        },
        {
            "input": ")) <span style=\"font-size:15pt\">Font-size change</span> ((",
            "expected_html": ")) <span style=\"font-size:15pt\">Font-size change</span> ((",
        },
        {
            "input": "[Elaine Aron]: *The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.*",
            "expected_html": "[Elaine Aron]: <em>The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.</em>",
        }
    ]

    for i, case in enumerate(test_cases):
        doc = MarkdownImporter(case["input"]).document
        result = HtmlExporter(doc, skip_header=True).output
        result = result.replace('<p>', '').replace('</p>', '')
        assert result == case["expected_html"], f"Failed test {i}: {result} != {case['expected_html']}"

test_markdown_importer()