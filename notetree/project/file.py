from dataclasses import dataclass, field
import json

class ProjectFileError(Exception):
    pass

class ProjectFileFormatError(ProjectFileError):
    pass

class ProjectFileVersionError(ProjectFileError):
    pass

@dataclass
class ProjectFile:
    file_version: str = '1.1'
    name: str = ''
    documents: list[dict] = field(default_factory=list)
    next_id: int = 1
    root_ids: list[int] = field(default_factory=list)

    def clear(self):
        self.name = ''
        self.documents.clear()
        self.next_id = 1
        self.root_ids.clear()

    def load(self, filename):
        # Load data from file
        try:
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ProjectFileFormatError(
                f"Invalid JSON in project file '{filename}' at line {e.lineno}, column {e.colno}."
            ) from e

        if not isinstance(data, dict):
            raise ProjectFileFormatError("Top-level JSON value must be an object.")

        file_version = data.get("file version")
        if file_version is None:
            raise ProjectFileFormatError("Missing required field: 'file version'.")
        if file_version != "1.1":
            raise ProjectFileVersionError(f"Unsupported project file version: {file_version!r}")

        name = data.get("name", "")
        if not isinstance(name, str):
            raise ProjectFileFormatError("'name' must be a string.")

        next_id = data.get("next id", 1)
        if not isinstance(next_id, int):
            raise ProjectFileFormatError("'next id' must be an integer.")
        elif next_id < 1:
            raise ProjectFileFormatError("'next id' must be a positive integer.")

        documents = data.get("documents", [])
        if not isinstance(documents, list):
            raise ProjectFileFormatError("'documents' must be a list.")
        for i, doc in enumerate(documents):
            if not isinstance(doc, dict):
                raise ProjectFileFormatError(f"'documents[{i}]' must be an object.")
            doc_id = doc.get("id")
            if doc_id is None:
                raise ProjectFileFormatError(f"Missed required field in 'documents[{i}]: 'id'.")
            elif not isinstance(doc_id, int):
                raise ProjectFileFormatError(f"The field 'id' in 'documents[{i}]' must be an integer.")
            elif doc_id >= next_id or doc_id < 1:
                raise ProjectFileFormatError(f"The field 'id' in 'documents[{i}]' (= {doc_id}) is out of range.")

        root_ids = data.get("roots", [])
        if not isinstance(root_ids, list):
            raise ProjectFileFormatError("'roots' must be a list.")
        for i, root_id in enumerate(root_ids):
            if not isinstance(root_id, int):
                raise ProjectFileFormatError(f"'roots[{i}]' must be an integer.")
            elif root_id >= next_id or root_id < 1:
                raise ProjectFileFormatError(f"'roots[{i}]' (= {root_id}) is out of range.")

        # The data has been validated
        # Assign local data to member variables

        self.file_version = file_version
        self.name = name
        self.documents = documents
        self.next_id = next_id
        self.root_ids = root_ids

    def save(self, filename):
        # Save data to file
        data = {'file version': self.file_version,
                'documents': self.documents,
                'roots': self.root_ids,
                'next id': self.next_id}

        if self.name:
            data['name'] = self.name

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
