from notetree.library.base.indexcounter import IndexCounter
from notetree.library.base.indexeddatacontainer import IndexedDataContainer

class Icons(IndexedDataContainer):
    def __init__(self):
        super().__init__('data/icons.json', IndexCounter.Type.Icon)

# Use Icons instance as Singleton
icons = Icons()
