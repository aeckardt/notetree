from functools import partial

from PyQt6.QtCore import (QObject, pyqtSignal, pyqtSlot, QModelIndex)
from PyQt6.QtGui import (QTextDocument)

from notetree.common.utils.settings import settings
from notetree.documenttree.treemodel import DocumentMetadata, DocumentTreeModel
from notetree.project.file import ProjectFile
from notetree.texteditor.markdown.exporter import MarkdownExporter
from notetree.texteditor.markdown.importer import MarkdownImporter

class ProjectModificationTracker(QObject):
    """
    Tracks project-level modification state.

    A project is considered modified if:
    - the document tree/model changed, or
    - one or more QTextDocument instances are modified.

    Selection/view state is intentionally not tracked here; that belongs to
    per-file UI settings.
    """
    changed = pyqtSignal(bool)

    def __init__(self):
        QObject.__init__(self)

        # Flag is set, if the document tree had
        # insert, edit, remove, move operations
        self.tree_modified = False

        # Any document that has unsaved changes,
        # will be in this list (identified by document id)
        self.modified_documents: set[int] = set()

    def is_modified(self) -> bool:
        return (
            self.tree_modified or 
            len(self.modified_documents) > 0
        )

    def _emit_if_changed(self, before: bool):
        after = self.is_modified()
        if after != before:
            self.changed.emit(after)

    @pyqtSlot()
    def clear(self):
        before = self.is_modified()
        self.tree_modified = False
        self.modified_documents.clear()
        self._emit_if_changed(before)

    @pyqtSlot()
    def mark_tree_modified(self):
        before = self.is_modified()
        self.tree_modified = True
        self._emit_if_changed(before)

    @pyqtSlot(int, bool)
    def set_document_modified(self, document_id: int, modified: bool):
        modified_before = self.is_modified()
        if modified:
            self.modified_documents.add(document_id)
        elif document_id in self.modified_documents:
            self.modified_documents.remove(document_id)
        if self.is_modified() != modified_before:
            self.changed.emit(self.is_modified())


class ProjectSession:
    def __init__(self):
        self.project = ProjectFile()
        self.filename: str | None = None
        self.file_cfg: dict | None = None
        self.mod_state = ProjectModificationTracker()
        self.model = DocumentTreeModel()
        self.documents: dict[int, QTextDocument] = {}

        self.model.inserted.connect(self._on_inserted)
        self.model.removed.connect(self._on_removed)
        self.model.data_changed.connect(self.mod_state.mark_tree_modified)

    def clear(self):
        # Remove all contents
        self.project.clear()
        self.filename = None
        self.file_cfg = None
        self.mod_state.clear()
        self._clear_documents()

        # Start over with empty session
        self.model.import_data(self.project)

    def load_from_file(self, filename: str):
        # Load project contents from file
        self.project.load(filename)
        self.filename = filename
        self.file_cfg = self._file_config(filename)

        # Clear previosly used documents
        self._clear_documents()

        # Import project data (document tree, icons and notes)
        # and build tree from flat structure
        self.model.import_data(self.project)

        # Import Markdown notes for each document as QTextDocument
        def import_markdown(index: QModelIndex):
            item: DocumentMetadata = index.internalPointer()
            slot = partial(self.mod_state.set_document_modified, item.id)
            document = MarkdownImporter(item.notes).document
            document.setModified(False)
            document.modificationChanged.connect(slot)
            self.documents[item.id] = document
        self.model.iterate_all(import_markdown)

        # Clear modification status
        self.mod_state.clear()

    def save_to_file(self, filename: str):
        # Export Markdown notes for each document from QTextDocument
        def export_markdown(index: QModelIndex):
            item: DocumentMetadata = index.internalPointer()
            document: QTextDocument = self.documents[item.id]
            item.notes = MarkdownExporter(document).output
        self.model.iterate_all(export_markdown)

        # Save model data (document tree, icons and notes)
        self.model.export_data(self.project)

        # Export data to filename
        self.project.save(filename)
        if filename != self.filename:
            self.filename = filename
            self.file_cfg = self._file_config(filename)

        # Mark QTextDocuments as clean after successful save
        for document in self.documents.values():
            document.setModified(False)

        # Clear modification status
        self.mod_state.clear()

    def recently_opened_document(self) -> int | None:
        if self.file_cfg is None:
            return None
        return self.file_cfg.get('recently opened')

    def set_recently_opened_document(self, item: DocumentMetadata | None):
        if self.file_cfg is None:
            # No filename available yet
            # Do nothing
            return
        if item is not None:
            self.file_cfg['recently opened'] = item.id
        elif 'recently opened' in self.file_cfg:
            del self.file_cfg['recently opened']

    def document(self, item: DocumentMetadata) -> QTextDocument:
        return self.documents[item.id]

    def _clear_documents(self):
        for document in self.documents.values():
            try:
                document.modificationChanged.disconnect()
            except TypeError:
                pass
        self.documents.clear()

    def _file_config(self, filename: str):
        file_array: list[dict] = settings.config('file config', [])
        for file_cfg in file_array:
            if filename != file_cfg['path']:
                # File names do not match
                continue
            # File found
            return file_cfg
        # File has not be registered yet
        # Append new item to list
        file_cfg = {"path": filename}
        file_array.append(file_cfg)
        return file_cfg

    def _on_inserted(self, item: DocumentMetadata):
        # Create an empty QTextDocument object for the newly created metadata
        document = QTextDocument()

        # Connect modification slot
        slot = partial(self.mod_state.set_document_modified, item.id)
        document.modificationChanged.connect(slot)

        # Map QTextDocument object to document ID
        self.documents[item.id] = document

    def _on_removed(self, item: DocumentMetadata):
        # Disconnect modification changed slot from document
        document = self.documents[item.id]
        try:
            document.modificationChanged.disconnect()
        except TypeError:
            pass

        # Remove QTextDocument from mapping
        self.documents.pop(item.id)