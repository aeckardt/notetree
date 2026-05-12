# NoteTree

NoteTree is a desktop writing and knowledge-organization application built with Python and PyQt6. It combines a tree-based project structure with a custom rich-text editor, allowing notes, references and longer text drafts to be organized in one workspace.

It was built organically from a personal need: collecting notes from books and online sources, structuring them into meaningful sections, and turning them into seminar material or longer essays. The current version focuses on the core foundation: project files with a document tree, rich-text editing, outline navigation, and Markdown/HTML import and export.

## Overview

A NoteTree project consists of multiple rich-text documents arranged hierarchically. This is useful for writing and research tasks where information needs to be split into smaller sections without losing the larger structure.

Example use cases:

- preparing a seminar or workshop
- collecting and organizing reading notes
- drafting essays or longer texts
- structuring personal research or project material

## Screenshots
![NoteTree workspace with document tree, rich-text editor and outline navigation](examples/notetree-demo/screenshot.png)

## Features

### Project workspace

- Create, open, save, and save-as project files
- Store multiple documents in a single project
- Restore recently opened files
- Restore window geometry and the last opened documents between sessions

### Document tree

The document hierarchy is shown in a tree view where nodes can be added, edited, removed, and rearranged by drag and drop.

A node consists of a document title and a selectable icon. A built-in icon selection is available, and custom icons can be added or removed through the dedicated icon manager.

### Rich-text editor

The editor supports the following formatting features:

- Headings levels 1-4
- Bold and italic text
- Font size changes
- Unordered lists
- Horizontal rules
- Inline links

A single document can also be exported as PDF using Qt’s printing/PDF infrastructure.

Copy, cut, and paste are implemented using HTML and plain-text MIME data. Markdown is used as part of the project’s document serialization and for import/export workflows. The HTML and Markdown parsers are limited to the formatting features currently supported by the editor.

### Outline navigation

NoteTree generates an outline from the headings in the current document.

The outline panel makes longer documents easier to navigate:

- headings are shown as a structured outline
- selecting an outline entry moves the editor cursor to that section

### Markdown and HTML support

NoteTree includes custom Markdown and HTML import/export code tailored to the editor’s supported formatting subset.

Currently supported Markdown-related features include:

- headings
- bold and italic inline formatting
- inline links
- unordered lists
- horizontal rules
- selected inline HTML spans used by the editor for font-size information

### Tests

The repository includes automated tests for the Markdown-related logic:

- Markdown importer
- Markdown exporter
- Markdown inline parser

These tests focus on the parsing and serialization behavior that is central to the editor’s Markdown interoperability.

## Running the application

This repository currently contains the application source code, but it is not yet packaged as an installable desktop application.
From the repository root, create a virtual environment and install the required runtime dependency:

```bash
python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install PyQt6
```

Then run the application:

```bash
python -m notetree.app
```

On Windows, activate the virtual environment with:

```bash
.venv\Scripts\activate
```

## Running tests
Install the test dependency:

```bash
python -m pip install pytest
```

Run the test suite from the repository root:

```bash
python -m pytest
```

## Technical Focus

NoteTree is primarily interesting as a structured PyQt6 desktop application rather than as a generic note-taking tool.
The project demonstrates work in several areas:

- PyQt6 desktop UI structure
- document tree model and view logic
- custom rich-text editor behavior
- custom PyQt6 widgets
- heading-based outline generation
- Markdown import/export
- HTML import/export
- inline formatting resolution
- project file serialization
- session and settings handling
- icon library and icon manager UI
- automated parser/exporter tests

The codebase is intentionally organized around these concerns, with separate modules for the document tree, text editor, Markdown/HTML handling, outline panel, project/session logic, common widgets, and icon management.

## Current limitations

NoteTree is functional, but it is not a complete word processor and does not aim to support every Markdown or HTML feature.
Current limitations include:

- Markdown and HTML support is limited to the subset used by the editor.
- Unsupported Markdown constructs are treated as plain text.
- Ordered lists, blockquotes, tables, and broader HTML/CSS support are not currently implemented.
- Linked images are recognized by parts of the import logic but are not exported as editor content.
- The application language follows the system default; a manual override is possible through the settings file.
- The repository does not currently provide a packaged installer.
- Automated tests currently focus on Markdown parsing/import/export rather than full UI behavior.

These limitations are intentional at the current stage. The project prioritizes a coherent, testable editing model over broad but incomplete document-format coverage.

## Roadmap

Possible future improvements include:

- implementing backlinks and a keyword index
- improving the application design
  - for example, reducing border for reduced visual disruption
- extending editor support for ordered lists, blockquotes, tables and images
  - and extending the Markdown/HTML parsers accordingly
- expanding automated tests beyond Markdown logic

Backlinks and a keyword index are especially relevant to the original purpose of the project: collecting notes from books and online sources, then organizing them into meaningful structures. A keyword could work like a tag: a lightweight marker that links related topics across different projects.

## License / third-party assets
This repository includes third-party icon assets. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and license information related to bundled assets.
