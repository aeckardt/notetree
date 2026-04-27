from dataclasses import dataclass

class ColumnFormat(int):
    String = 1
    Int = 2

@dataclass
class Column:
    caption: str
    key: str
    format: ColumnFormat
    sort_by_table_contents: bool = True
