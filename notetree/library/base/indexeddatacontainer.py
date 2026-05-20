import os
import json

from PyQt6.QtCore import (QObject, pyqtSignal)

from notetree.library.base.indexcounter import IndexCounter, indexcounter

class IndexedDataContainer(QObject):
    loaded = pyqtSignal()
    removed = pyqtSignal(int)
    inserted = pyqtSignal(int)
    moved = pyqtSignal(int, int)
    updated = pyqtSignal(int)

    def __init__(self, filename: str, index_type: IndexCounter.Type):
        super().__init__()

        self._filename = filename
        self._index_type = index_type

        self._data = []
        self._index_to_pos = {}

    def __getitem__(self, pos):
        return self._data[pos]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        self.__n = 0
        return self

    def __next__(self):
        if self.__n < len(self._data):
            dataset = self._data[self.__n]
            self.__n += 1
            return dataset
        else:
            raise StopIteration

    def append(self, dataset):
        new_index = indexcounter.next(self._index_type)
        new_pos = len(self._data)

        dataset['index'] = new_index
        self._data.append(dataset)
        self._index_to_pos[new_index] = new_pos
        indexcounter.inc(self._index_type)

        self.inserted.emit(new_index)

    def from_index(self, index) -> dict:
        if index not in self._index_to_pos:
            raise Exception('Index not contained in data')
        pos = self._index_to_pos[index]
        return self._data[pos]

    def load(self):
        if not os.path.isfile(self._filename):
            self._data = []
            self._index_to_pos = {}
            return

        with open(self._filename, 'r', encoding='utf-8') as f:
            self._data = json.load(f)

        self._setup_index_to_pos()
        self.loaded.emit()

    def remove(self, dataset):
        index = dataset['index']
        pos = self._index_to_pos[index]

        # Remove dataset
        self._index_to_pos.pop(index)
        self._data.pop(pos)

        # Update index_to_pos mapping
        for _index in self._index_to_pos.keys():
            _pos = self._index_to_pos[_index]
            if _pos > pos:
                self._index_to_pos[_index] -= 1

        self.removed.emit(index)

    def save(self):
        with open(self._filename, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=4, sort_keys=True,
                      separators=(',', ': '), ensure_ascii=False)

    def update(self, dataset):
        index = dataset['index']
        if index not in self._index_to_pos:
            raise Exception('Index not contained in data')

        pos = self._index_to_pos[index]
        self._data[pos] = dataset

        self.updated.emit(index)

    def _setup_index_to_pos(self):
        self._index_to_pos = {}
        for pos in range(len(self._data)):
            dataset = self._data[pos]
            self._index_to_pos[dataset['index']] = pos
