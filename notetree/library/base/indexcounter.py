import os
import json

class IndexCounter:
    class Type(int):
        Icon = 4

    def __init__(self):
        self._data = {}

    def next(self, type: Type):
        key = self._key(type)
        if key not in self._data or 'next index' not in self._data[key]:
            if os.path.isfile(f'{key}.json'):
                with open(f'{key}.json') as f:
                    data = json.load(f)
            else:
                data = []
            max_index = 0
            for dataset in data:
                if 'index' in dataset and dataset['index'] > max_index:
                    max_index = dataset['index']
            self._data[key] = {'next index': max_index + 1}
        return self._data[key]['next index']

    def inc(self, type: Type):
        key = self._key(type)
        next_index = self.next(type)
        self._data[key]['next index'] = next_index + 1

    def load(self):
        if os.path.isfile('data/index.json'):
            with open('data/index.json', 'r') as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def save(self):
        with open('data/index.json', 'w') as f:
            json.dump(self._data, f, indent = 4, sort_keys = True,
                      separators=(',', ': '), ensure_ascii = False)

    def _key(self, type: Type):
        return {
            IndexCounter.Type.Icon: 'icons'
        }[type]


# Use IndexCounter instance as Singleton
indexcounter = IndexCounter()
