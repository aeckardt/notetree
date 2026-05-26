from PyQt6.QtGui import (QTextCursor)

from notetree.texteditor.html.importer import HtmlImporter
from notetree.texteditor.markdown.exporter import MarkdownExporter

def test_markdown_export():
    test_cases = [
        {
            "input": "<h1>A <em>nice</em> heading</h1>",
            "expected_markdown": "# A *nice* heading",
        },
        {
            "input": "<h1>A <a href=\"https://example.com\">linked</a> heading",
            "expected_markdown": "# A [linked](https://example.com) heading"
        },
        {
            "input": "<h1>A <ins>marked</ins> heading",
            "expected_markdown": "# A <ins>marked</ins> heading"
        },
        {
            "input": """<p><strong>[Interviewer]: Are HSP more prone to depression and anxiety?</strong></p><p>[Elaine Aron]: <em>With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at <a href="http://hsperson.com">hsperson.com</a>, research tab). When HSPs have had good-enough childhoods and/or are living in not too stressful conditions, they are actually less prone to depression, and somewhat less to anxiety as well. (The issue with anxiety is that all HSPs are more aware of dangers as well as opportunities and process these more deeply. Hence, what is a normal level of anxiety/worry for HSPs would be different for those less aware of dangers.) If they have had an adverse childhood environment, they are more susceptible to depression, anxiety, shyness, and poor health.</em>""",
            "expected_markdown": """**[Interviewer]: Are HSP more prone to depression and anxiety?**
[Elaine Aron]: *With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at [hsperson.com](http://hsperson.com), research tab). When HSPs have had good-enough childhoods and/or are living in not too stressful conditions, they are actually less prone to depression, and somewhat less to anxiety as well. (The issue with anxiety is that all HSPs are more aware of dangers as well as opportunities and process these more deeply. Hence, what is a normal level of anxiety/worry for HSPs would be different for those less aware of dangers.) If they have had an adverse childhood environment, they are more susceptible to depression, anxiety, shyness, and poor health.*"""
        },
        {
            "input": "Normal text before. And then: <a href=\"https://google.com\"><ins>This is </ins><em>a wildly </em></a><em><strong>complicated</strong></em><strong><a href=\"https://chatgpt.com\"><ins> styled block</ins></a></strong> example",
            "expected_markdown": "Normal text before. And then: [<ins>This is</ins> *a wildly*](https://google.com) ***complicated* <ins>[styled block](https://chatgpt.com)</ins>** example"
        },
        {
            "input": "Font <span style=\"font-size:15pt\">size</span><span style=\"font-size:14pt\"> test</span>.",
            "expected_markdown": "Font <span style=\"font-size:15pt\">size</span> <span style=\"font-size:14pt\">test</span>."
        },
        {
            "input": """<p><strong>[Interviewer]: Are HSP more prone to depression and anxiety?</strong></p><p>[Elaine Aron]: <em>With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at <a href="http://hsperson.com">hsperson.com</a>, research tab). When HSPs have had good-enough childhoods and/or are living in not too stressful conditions, they are actually less prone to depression, and somewhat less to anxiety as well. (The issue with anxiety is that all HSPs are more aware of dangers as well as opportunities and process these more deeply. Hence, what is a normal level of anxiety/worry for HSPs would be different for those less aware of dangers.) If they have had an adverse childhood environment, they are more susceptible to depression, anxiety, shyness, and poor health.</em>""",
            "range": {"start": 0, "end": 13},
            "expected_markdown": "**[Interviewer]**"
        },
        {
            "input": """<p><strong>[Interviewer]: Are HSP more prone to depression and anxiety?</strong></p><p>[Elaine Aron]: <em>With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at <a href="http://hsperson.com">hsperson.com</a>, research tab). When HSPs have had good-enough childhoods and/or are living in not too stressful conditions, they are actually less prone to depression, and somewhat less to anxiety as well. (The issue with anxiety is that all HSPs are more aware of dangers as well as opportunities and process these more deeply. Hence, what is a normal level of anxiety/worry for HSPs would be different for those less aware of dangers.) If they have had an adverse childhood environment, they are more susceptible to depression, anxiety, shyness, and poor health.</em>""",
            "range": {"start": 61, "end": 199},
            "expected_markdown": "[Elaine Aron]: *With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at* "
        },
        {
            "input": """<p><strong>[Interviewer]: Are HSP more prone to depression and anxiety?</strong></p><p>[Elaine Aron]: <em>With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at <a href="http://hsperson.com">hsperson.com</a>, research tab). When HSPs have had good-enough childhoods and/or are living in not too stressful conditions, they are actually less prone to depression, and somewhat less to anxiety as well. (The issue with anxiety is that all HSPs are more aware of dangers as well as opportunities and process these more deeply. Hence, what is a normal level of anxiety/worry for HSPs would be different for those less aware of dangers.) If they have had an adverse childhood environment, they are more susceptible to depression, anxiety, shyness, and poor health.</em>""",
            "range": {"start": 61, "end": 200},
            "expected_markdown": "[Elaine Aron]: *With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at [h](http://hsperson.com)*"
        },
        {
            "input": """<p><strong>[Interviewer]: Are HSP more prone to depression and anxiety?</strong></p><p><span style="font-size:15pt">[Elaine Aron]: <em>With HSPs, it is always a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at <a href="http://hsperson.com">hsperson.com</a>, research tab). When HSPs have had good-enough childhoods and/or are living in not too stressful conditions, they are actually less prone to depression, and somewhat less to anxiety as well. (The issue with anxiety is that all HSPs are more aware of dangers as well as opportunities and process these more deeply. Hence, what is a normal level of anxiety/worry for HSPs would be different for those less aware of dangers.) If they have had an adverse childhood environment, they are more susceptible to depression, anxiety, shyness, and poor health.</em></span>""",
            "range": {"start": 100, "end": 207},
            "expected_markdown": """*<span style="font-size:15pt">a matter of differential susceptibility (see studies by Michael Pluess, Jay Belsky, and others, at [hsperson](http://hsperson.com)</span>*"""
        },
        {
            "input": "[Elaine Aron]: <em>The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.</em>",
            "expected_markdown": "[Elaine Aron]: *The association [to Neuroticism] with sensitivity is through anxiety. HSPs are more aware than others of both risks and opportunities. If you notice more risks, you will be more anxious, so Neuroticism is in a sense a normal part of the trait, although it can certainly be increased with negative experiences.*"
        }
    ]

    for i, case in enumerate(test_cases):
        doc = HtmlImporter(case["input"]).document
        if "range" in case:
            start = case["range"]["start"]
            end = case["range"]["end"]
            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            output = MarkdownExporter(doc, cursor).output
        else:
            output = MarkdownExporter(doc).output
        assert output == case["expected_markdown"], f"Failed test {i}: {output} != {case['expected_markdown']}"

test_markdown_export()