from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, Qt)

from notetree.library.base.column import Column, ColumnFormat
from notetree.library.base.indexeddatacontainer import IndexedDataContainer

class IndexedTableModel(QAbstractTableModel):
    def __init__(self, data: IndexedDataContainer):
        super().__init__()

        data.loaded.connect(self._on_loaded)
        data.removed.connect(self._on_removed)
        data.inserted.connect(self._on_inserted)
        data.moved.connect(self._on_moved)
        data.updated.connect(self._on_updated)

        self._data = data
        self._columns = []
        self._selected_columns = None

        self._on_loaded()

    def add_column(self, caption, key, format, sort_by_table_contents: bool = True):
        self._columns.append(Column(caption, key, format, sort_by_table_contents))

    def columnCount(self, parent=...):
        if self._selected_columns is None:
            return len(self._columns)
        else:
            return len(self._selected_columns)

    def column_def(self, column) -> Column:
        if self._selected_columns is None:
            return self._columns[column]
        else:
            return self._columns[self._selected_columns[column]]

    def filter(self, predicate):
        self.beginResetModel()
        self._indexes = []
        for dataset in self._data:
            if predicate(dataset):
                self._indexes.append(dataset['index'])
        self._use_filter = True
        self._filter_predicate = predicate
        self.endResetModel()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return super().headerData(section, orientation, role)
        if self._selected_columns is None:
            return self._columns[section].caption
        else:
            return self._columns[self._selected_columns[section]].caption

    def item_at(self, row):
        return self._data.from_index(self._indexes[row])

    def key(self, column):
        if self._selected_columns is None:
            return self._columns[column].key
        else:
            return self._columns[self._selected_columns[column]].key

    def remove_filter(self):
        if not self._use_filter:
            return
        self.beginResetModel()
        self._indexes = []
        for dataset in self._data:
            self._indexes.append(dataset['index'])
        self._use_filter = False
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...):
        if not self._use_filter:
            return len(self._data)
        else:
            return len(self._indexes)

    def set_table_columns(self, columns):
        self.beginResetModel()
        self._selected_columns = columns
        self.endResetModel()

    def sort(self, column, order):
        self.beginResetModel()

        _column_def = self.column_def(column)
        _key = self.key(column)

        if _column_def.sort_by_table_contents:
            # Sort by table contents
            data = {}
            row = 0
            for index in self._indexes:
                data[index] = self.data(self.index(row, column, QModelIndex()), Qt.ItemDataRole.DisplayRole)
                if _column_def.format == ColumnFormat.String:
                    data[index] = str(data[index]).lower()
                elif _column_def.format == ColumnFormat.Int:
                    if type(data[index]) == str:
                        if str(data[index]).isnumeric():
                            data[index] = int(data[index])
                        else:
                            data[index] = 0
                row += 1
            self._indexes = sorted(self._indexes, key=lambda index: data[index],
                                   reverse=order == Qt.SortOrder.DescendingOrder)
        else:
            # Sort by original data
            if _column_def.format == ColumnFormat.String:
                self._indexes = sorted(self._indexes, key=lambda index: self._data.from_index(index).get(_key, ''),
                                       reverse=order == Qt.SortOrder.DescendingOrder)
            elif _column_def.format == ColumnFormat.Int:
                self._indexes = sorted(self._indexes, key=lambda index: self._data.from_index(index).get(_key, 0),
                                       reverse=order == Qt.SortOrder.DescendingOrder)

        self._use_sorting = True
        self._sort_column = column
        self._sort_order = order

        self.endResetModel()

    def _on_loaded(self):
        self._indexes = []
        for dataset in self._data:
            self._indexes.append(dataset['index'])

        self._use_filter = False
        self._filter_predicate = None

        self._use_sorting = False
        self._sort_column = None
        self._sort_order = None

    def _on_removed(self, index):
        if index not in self._indexes:
            return
        row = self._indexes.index(index)
        self.beginRemoveRows(QModelIndex(), row, row)
        self.endRemoveRows()
        self._indexes.remove(index)

    def _on_inserted(self, index):
        dataset = self._data.from_index(index)
        if self._use_filter:
            if (self._filter_predicate(dataset)):
                self._indexes.append(index)
        else:
            self._indexes.append(index)
        if self._use_sorting:
            self.sort(self._sort_column, self._sort_order)
        row = self._indexes.index(index)
        self.beginInsertRows(QModelIndex(), row, row)
        self.endInsertRows()

    def _on_moved(self, index1, index2):
        if index1 not in self._indexes or index2 not in self._indexes:
            return
        row1 = self._indexes.index(index1)
        row2 = self._indexes.index(index2)
        self.beginMoveRows(QModelIndex(), row1, row1, QModelIndex(), row2)
        self.endMoveRows

    def _on_updated(self, index):
        pass
