from notetree.texteditor.markdown.inlineparser import InlineNode, MarkdownInlineParser

def test_markdown_inlineparser():
    test_cases = [
        {
            "input": """***bold and italic* still open**""",
            "expected_ast": "<strong><em>bold and italic</em> still open</strong>"
        },
        {
            "input": "*italic with **mismatch* bold**",
            "expected_ast": "<em>italic with <em><em>mismatch</em> bold</em></em>"
        },
        {
            "input": "*x* **y**",
            "expected_ast": "<em>x</em> <strong>y</strong>"
        },
        {
            "input": "*x **y***",
            "expected_ast": "<em>x <strong>y</strong></em>"
        },
        {
            "input": "*x **y** z*",
            "expected_ast": "<em>x <strong>y</strong> z</em>"
        },
        {
            "input": "***x y***",
            "expected_ast": "<strong><em>x y</em></strong>"
        },
        {
            "input": "***x y* z**",
            "expected_ast": "<strong><em>x y</em> z</strong>"
        },
        {
            "input": "***x y** z*",
            "expected_ast": "<em><strong>x y</strong> z</em>"
        },
        {
            "input": "**x *y***",
            "expected_ast": "<strong>x <em>y</em></strong>"
        },
        {
            "input": "**x *y* z**",
            "expected_ast": "<strong>x <em>y</em> z</strong>"
        },
        {
            "input": "**bold *and italic* inside**",
            "expected_ast": "<strong>bold <em>and italic</em> inside</strong>"
        },
        {
            "input": "*italic **and bold** inside*",
            "expected_ast": "<em>italic <strong>and bold</strong> inside</em>"
        },
        {
            "input": "*unclosed italic",
            "expected_ast": "*unclosed italic"  # fallback to plain text
        },
        {
            "input": "**unclosed bold",
            "expected_ast": "**unclosed bold"
        },
        {
            "input": "***bold and italic***",
            "expected_ast": "<strong><em>bold and italic</em></strong>"
        },
        {
            "input": "*[*unmatched italic](https://google.com)",
            "expected_ast": "*<a href=\"https://google.com\">*unmatched italic</a>"
        },
        {
            "input": "*[*broken italic link*](https://googl)",
            "expected_ast": "*<a href=\"https://googl\"><em>broken italic link</em></a>"
        },
        {
            "input": "*![*image test***](img/file_on_my_computer.png)",
            "expected_ast": "*<img src=\"img/file_on_my_computer.png\"><em>image test</em>**</img>"
        },
        {
            "input": "[This is not a link](because of the whitespace)",
            "expected_ast": "[This is not a link](because of the whitespace)"
        },
        {
            "input": "[This is not a valid link]((because_of_double_parentheses))",
            "expected_ast": "[This is not a valid link]((because_of_double_parentheses))"
        },
        {
            "input": "[This is a valid link](  however  )",
            "expected_ast": "<a href=\"however\">This is a valid link</a>"
        },
        {
            "input": "<span style=\"font-size:15pt\"><ins>This is an HTML</ins></span> test.",
            "expected_ast": "<span style=\"font-size:15pt\"><ins>This is an HTML</ins></span> test.",
        },
        {
            "input": "This <- is not meant to be interpreted as HTML. And -> this neither.",
            "expected_ast": "This <- is not meant to be interpreted as HTML. And -> this neither.",
        },
        {
            "input": "> The blockquote feature is not implemented yet.",
            "expected_ast": "> The blockquote feature is not implemented yet.",
        },
        {
            "input": "Non-<ins><strong>matching HTML</ins></strong> tags.",
            "expected_ast": "Non-<ins><strong>matching HTML</ins></strong> tags.",
        },
        {
            "input": "<ins>Overlapping **</ins>styles not resolved**",
            "expected_ast": "<ins>Overlapping **</ins>styles not resolved**",
        },
        {
            "input": "**<ins>Composite styles resolved</ins>**",
            "expected_ast": "<strong><ins>Composite styles resolved</ins></strong>",
        },
        {
            "input": ")) <span style=\"font-size:15pt\">Font-size change</span> ((",
            "expected_ast": ")) <span style=\"font-size:15pt\">Font-size change</span> ((",
        },
        {
            "input": "<span style=\"font-size:15pt\">[Elaine Aron]: *Naturally they do, partly because stress often manifests as somatic symptoms, and they are often under more stress. Somatic symptoms can also be the result of dissociated trauma, and HSPs have often been exposed to trauma.*</span>",
            "expected_ast": "<span style=\"font-size:15pt\">[Elaine Aron]: <em>Naturally they do, partly because stress often manifests as somatic symptoms, and they are often under more stress. Somatic symptoms can also be the result of dissociated trauma, and HSPs have often been exposed to trauma.</em></span>"
        },
        {
            "input": "[Elaine Aron]: *The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.*",
            "expected_ast": "[Elaine Aron]: <em>The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.</em>",
        },
        {
            "input": "<span style=\"font-size:15pt\">[Elaine Aron]: *The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.*</span>",
            "expected_ast": "<span style=\"font-size:15pt\">[Elaine Aron]: <em>The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.</em></span>",
        }
    ]

    def generate_ast_html(node: InlineNode) -> str:
        Type = InlineNode.Type
        output = ''

        match node.type:
            case Type.STRONG:
                output += '<strong>'
            case Type.EMPH:
                output += '<em>'
            case Type.INLINE_LINK:
                output += f'<a href="{node.attrs['href']}">'
            case Type.IMAGE:
                output += f'<img src="{node.attrs['src']}">'
            case Type.HTML_TAG:
                attr_str = ''
                if node.attrs:
                    for attr_name in node.attrs.keys():
                        attr_str += f' {attr_name}="{node.attrs[attr_name]}"'
                output += f'<{node.content}{attr_str}>'
            case Type.TEXT:
                return node.content

        for child in node.children:
            output += generate_ast_html(child)

        match node.type:
            case Type.STRONG:
                output += '</strong>'
            case Type.EMPH:
                output += '</em>'
            case Type.INLINE_LINK:
                output += '</a>'
            case Type.IMAGE:
                output += '</img>'
            case Type.HTML_TAG:
                output += f'</{node.content}>'

        return output

    for case in test_cases:
        ast = MarkdownInlineParser(case["input"]).ast_root
        result = generate_ast_html(ast)
        assert result == case["expected_ast"]

test_markdown_inlineparser()