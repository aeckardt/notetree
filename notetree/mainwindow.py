import pathlib

from PyQt6.QtCore import (QMetaObject, Qt, QItemSelectionModel, QModelIndex, QCoreApplication,
                          QFileInfo, pyqtSlot)
from PyQt6.QtGui import (QCloseEvent, QKeySequence, QAction)
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSplitter, QMessageBox, QMenuBar, QMenu,
                             QFileDialog)

from notetree.common.utils.errormessage import show_error_msg
from notetree.common.utils.settings import settings
from notetree.documenttree.treemodel import DocumentNode
from notetree.documenttree.treewidget import DocumentTreeWidget
from notetree.library.icons.managerdialog import IconManagerDialog
from notetree.outline import OutlineItem, TableOfContents
from notetree.project.file import ProjectFileVersionError, ProjectFileFormatError
from notetree.project.session import ProjectSession
from notetree.texteditor.editor import TextEditorWidget

MAX_RECENT_FILES = 10

class MainWindow(QMainWindow):
    # -----------------------------------------------
    # 1. Constructor / Initialization
    # -----------------------------------------------

    def __init__(self, parent: QWidget = None):
        QMainWindow.__init__(self, parent)

        # Initialize project session
        self.session = ProjectSession()
        self.mod_state = self.session.mod_state
        self.mod_state.changed.connect(self.setWindowModified)
        self.model = self.session.model

    def setup_ui(self):
        self.setObjectName("mainwindow")
        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.h_splitter = QSplitter()
        self.h_splitter.setOrientation(Qt.Orientation.Horizontal)

        layout1 = QVBoxLayout()
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(5)

        self.v_splitter = QSplitter()
        self.v_splitter.setOrientation(Qt.Orientation.Vertical)

        self.document_tree = DocumentTreeWidget(self.tr("Structure"), model=self.model)
        self.document_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.treeview = self.document_tree.treeview
        self.v_splitter.addWidget(self.document_tree)

        self.document_tree.selection_changed.connect(self._on_selection_changed, Qt.ConnectionType.DirectConnection)

        self.table_of_contents = TableOfContents(self.tr("Outline"))
        self.table_of_contents.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.v_splitter.addWidget(self.table_of_contents)

        self.table_of_contents.selection_changed.connect(self._on_toc_selection_changed, Qt.ConnectionType.DirectConnection)

        layout1.addWidget(self.v_splitter, 3)

        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        layout2.setSpacing(5)

        self.editor = TextEditorWidget()
        self.editor.setEnabled(False)
        layout2.addWidget(self.editor, 1)

        widget1 = QWidget()
        widget1.setLayout(layout1)

        widget2 = QWidget()
        widget2.setLayout(layout2)

        self.h_splitter.addWidget(widget1)
        self.h_splitter.addWidget(widget2)

        layout.addWidget(self.h_splitter)

        self.centralwidget.setLayout(layout)
        self.setCentralWidget(self.centralwidget)

        self._setup_menu()
        self.setWindowTitle(self.tr("NoteTree"))

        QMetaObject.connectSlotsByName(self)

        settings.restore_geometry(self)
        wnd_config = settings.window_config(self)
        if 'view heights' in wnd_config:
            self.v_splitter.setSizes(wnd_config['view heights'])
        if 'splitter sizes' in wnd_config:
            self.h_splitter.setSizes(wnd_config['splitter sizes'])

        self._reopen_last_file()

    def _setup_menu(self):
        # Setup menubar
        self.menubar = QMenuBar(self)
        self.menubar.setObjectName("menubar")
        self.file_menu = QMenu(self.menubar)
        self.edit_menu = QMenu(self.menubar)

        # New action
        self.new_action = QAction(self)
        self.new_action.setObjectName("NewAction")
        self.new_action.setText(self.tr("New File..."))
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.triggered.connect(self._on_new)

        # Open action
        self.open_action = QAction(self)
        self.open_action.setObjectName("openAction")
        self.open_action.setText(self.tr("Open..."))
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self._on_open)

        # Open recent action
        self.recent_files_menu = QMenu(self.file_menu)
        self.recent_files_menu.setObjectName("menuRecentFiles")
        self.recent_files_menu.setTitle(self.tr("Open Recent"))
        self._setup_recent_file_actions()

        # Save action
        self.save_action = QAction(self)
        self.save_action.setObjectName("saveAction")
        self.save_action.setText(self.tr("Save"))
        self.save_action.setEnabled(False)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.mod_state.changed.connect(self.save_action.setEnabled)
        self.save_action.triggered.connect(self._on_save)

        # Save As action
        self.save_as_action = QAction(self)
        self.save_as_action.setObjectName("saveAsAction")
        self.save_as_action.setText(self.tr("Save As..."))
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self._on_save_as)

        # Exit action
        self.exit_action = QAction(self)
        self.exit_action.setObjectName("exitAction")
        self.exit_action.setText(self.tr("Exit"))
        self.exit_action.setMenuRole(QAction.MenuRole.QuitRole)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)

        # Assemble file menu
        self.file_menu.setObjectName("menuFile")
        self.file_menu.setTitle(self.tr("File"))
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addMenu(self.recent_files_menu)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)
        self.menubar.addAction(self.file_menu.menuAction())

        # -----------------------------------------------------------------

        # Edit Icons action
        self.edit_icons_action = QAction(self)
        self.edit_icons_action.setObjectName("edit_icons")
        self.edit_icons_action.setText(self.tr("Icons"))
        self.edit_icons_action.setShortcut("Ctrl+Shift+I")
        self.edit_icons_action.triggered.connect(self._on_edit_icons)

        # Assemble edit menu
        self.edit_menu.setObjectName("menuEdit")
        self.edit_menu.setTitle(self.tr("Edit"))
        self.edit_menu.addAction(self.edit_icons_action)
        self.menubar.addAction(self.edit_menu.menuAction())

        self.setMenuBar(self.menubar)

    def _setup_recent_file_actions(self):
        def open_recent(n):
            return lambda: self._on_open_recent(n)

        self.recent_file_paths: list[str] = settings.config('recent files', [])
        self.recent_file_actions: list[QAction] = []

        for n in range(MAX_RECENT_FILES):
            open_recent_action = QAction(self)
            open_recent_action.setObjectName(f'openRecent{n}Action')
            open_recent_action.setVisible(False)
            if n <= 9:
                keymod = (n + 1) % 10
                open_recent_action.setShortcut(QKeySequence(f"Ctrl+Alt+{str(keymod)}"))
            self.recent_file_actions.append(open_recent_action)
            self.recent_files_menu.addAction(open_recent_action)
            open_recent_action.triggered.connect(open_recent(n))

        self._update_recent_action_list()

    # -----------------------------------------------
    # 2. Event handlers
    # -----------------------------------------------

    def closeEvent(self, event: QCloseEvent):
        if self._try_save_file():
            event.accept()
        else:
            event.ignore()

        settings.save_geometry(self)
        wnd_dict = settings.config(self.__class__.__name__)
        wnd_dict['view heights'] = self.v_splitter.sizes()
        wnd_dict['splitter sizes'] = self.h_splitter.sizes()

    # -----------------------------------------------
    # 3. Menu action slots
    # -----------------------------------------------

    @pyqtSlot()
    def _on_new(self):
        # Make sure there are no unsaved changes
        if not self._try_save_file():
            # The action has been cancelled by the user
            return

        self.session.clear()
        self._open_document(QModelIndex())
        self.setWindowTitle(self.tr("NoteTree"))

    @pyqtSlot()
    def _on_open(self):
        # Make sure there are no unsaved changes
        if not self._try_save_file():
            # The action has been cancelled by the user
            return

        # Open file dialog to select file
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Open project"), None, self.tr("Projects") + " (*.json)")

        # If a file has been selected, the file path should contain at least one character
        if len(file_path) > 0:
            self._open_file(file_path)

    @pyqtSlot(int)
    def _on_open_recent(self, index: int):
        # Make sure there are no unsaved changes
        if not self._try_save_file():
            # The action has been cancelled by the user
            return

        sender: QAction = self.recent_file_actions[index]
        try:
            self._open_file(sender.data())
        except FileNotFoundError:
            show_error_msg(self.tr("The file could not be found."), self)

            # Remove entry from recent files
            self.recent_file_paths.pop(index)

            self._update_recent_action_list()

    @pyqtSlot()
    def _on_save(self):
        self._save_to_file()

    @pyqtSlot()
    def _on_save_as(self):
        self._save_to_file(True)

    @pyqtSlot()
    def _on_edit_icons(self):
        editor = IconManagerDialog(self.tr("Edit icons"))
        editor.exec()

    # -----------------------------------------------
    # 4. Open / Save file
    # -----------------------------------------------

    def _open_file(self, filename):
        if filename == self.session.filename:
            return

        self._load_from_file(filename)

    def _load_from_file(self, filename):
        # Load project contents from file
        try:
            self.session.load_from_file(filename)
        except ProjectFileVersionError as e:
            show_error_msg(f"{self.tr("Unsupported file version.")}\n\n{str(e)}", self)
            return
        except ProjectFileFormatError as e:
            show_error_msg(f"{self.tr("An error occurred while reading the project file.")}\n\n{str(e)}", self)
            return

        # Load ID of recently opened document from global settings
        recently_opened_id = self.session.recently_opened_document()

        # Reopen recently opened document (if available)
        if recently_opened_id is not None:
            def open_page(index: QModelIndex):
                node = index.internalPointer()
                if node.id == recently_opened_id:
                    ModelSelectionFlag = QItemSelectionModel.SelectionFlag
                    command = ModelSelectionFlag.ClearAndSelect | ModelSelectionFlag.Rows
                    self.treeview.selectionModel().select(index, command)
            self.model.iterate(open_page)
        else:
            self._open_document(QModelIndex())

        # Reset modification status
        self.editor.textedit.document().setModified(False)
        self.editor.textedit.setFocus()

        # Change window title according to filename
        stripped_name = QFileInfo(filename).fileName()
        self.setWindowTitle(self.tr("NoteTree") + f" - {stripped_name}")

        # Pass on file directory to treeview and notes_edit
        root_directory = pathlib.Path(filename).parent.resolve()
        self.editor.textedit.root_directory = root_directory

        # Update recent files list
        self._append_to_recent_files_list(filename)
        self._update_recent_action_list()

    def _save_to_file(self, prompt_filename: bool = False) -> bool:
        if self.session.filename is None or prompt_filename:
            # Open file dialog to specify path for new file
            filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save project"), None, self.tr("Projects") + " (*.json)")

            if len(filename) == 0:
                # No file has been specified
                return False
        else:
            filename = self.session.filename

        # Save project to file
        self.session.save_to_file(filename)

        # Save ID of recently opened document to global settings
        meta = self._get_document_metadata(self.document_tree.selected_index)
        self.session.set_recently_opened_document(meta.id)

        # Update recent files list
        self._append_to_recent_files_list(filename)
        self._update_recent_action_list()

        return True

    def _try_save_file(self):
        """
        Check if the currently opened project has any changes
        and ask the user if they should be saved.

        Returns True, if the project file can be closed.
        Returns False, if the action should be cancelled.
        """
        if not self.mod_state.is_modified():
            return True

        Button = QMessageBox.StandardButton

        # Setup MessageBox
        msgbox = QMessageBox(QMessageBox.Icon.Warning, QCoreApplication.applicationName(),
                             self.tr("The current project has been modified.\nDo you want to save your changes?"),
                             Button.Save | Button.Discard | Button.Cancel, self)
        msgbox.button(Button.Save).setText(self.tr("&Save"))
        msgbox.button(Button.Discard).setText(self.tr("&Discard"))
        msgbox.button(Button.Cancel).setText(self.tr("&Cancel"))

        # Execute MessageBox with return value 'msgId'
        msg_id = msgbox.exec()

        # Handle the user input accordingly
        match msg_id:
            case Button.Save:
                return self._save_to_file()
            case Button.Cancel:
                return False
            case Button.Discard:
                return True

    # -----------------------------------------------
    # 5. Recent files handlers
    # -----------------------------------------------

    def _reopen_last_file(self):
        open_recent_action: QAction = self.recent_file_actions[0]
        if open_recent_action.isVisible():
            self._on_open_recent(0)

    def _append_to_recent_files_list(self, filename: str):
        # Update recent files list
        if filename in self.recent_file_paths:
            self.recent_file_paths.remove(filename)
        self.recent_file_paths.insert(0, filename)
        if len(self.recent_file_paths) > MAX_RECENT_FILES:
            self.recent_file_paths.pop()

    def _update_recent_action_list(self):
        for n in range(len(self.recent_file_paths)):
            stripped_name = QFileInfo(self.recent_file_paths[n]).fileName()
            open_recent_action = self.recent_file_actions[n]
            open_recent_action.setText(stripped_name)
            open_recent_action.setData(self.recent_file_paths[n])
            open_recent_action.setVisible(True)

        if len(self.recent_file_paths) < MAX_RECENT_FILES:
            rest = MAX_RECENT_FILES - len(self.recent_file_paths)
            for n in range(rest):
                self.recent_file_actions[-n - 1].setVisible(False)

    # -----------------------------------------------
    # 6. Private methods - DocumentTreeWidget slots
    # -----------------------------------------------

    @pyqtSlot(QModelIndex, QModelIndex)
    def _on_selection_changed(self, selected, deselected):
        self._open_document(selected)

    def _open_document(self, index: QModelIndex):
        meta = self._get_document_metadata(index)
        if meta is not None:
            document = self.session.document(meta.id)
            self.editor.textedit.set_document(document)
            self.editor.setEnabled(True)
            self.table_of_contents.set_text_document(document)
        else:
            # Clear all contents
            self.editor.textedit.clear()
            self.editor.setEnabled(False)
            self.table_of_contents.clear()

        self.session.set_recently_opened_document(meta.id)

    # -----------------------------------------------
    # 7. Private methods - TableOfConents slots
    # -----------------------------------------------

    @pyqtSlot(QModelIndex)
    def _on_toc_selection_changed(self, selected):
        if selected.isValid():
            item: OutlineItem = selected.internalPointer()
        else:
            return

        block_index = item.block_index()
        document = self.editor.textedit.document()

        scrollbar = self.editor.textedit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        block = document.findBlockByNumber(block_index)
        cursor = self.editor.textedit.textCursor()
        cursor.setPosition(block.position())
        self.editor.textedit.setTextCursor(cursor)

    # -----------------------------------------------
    # 8. Static/Utility Methods
    # -----------------------------------------------

    def _get_document_metadata(self, index: QModelIndex) -> DocumentNode | None:
        if index.isValid():
            return index.internalPointer()
        return None
