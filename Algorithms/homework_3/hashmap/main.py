import copy
import gc
import time


class HashMap:
    def _create_empty_storage(self):
        self.storage = [[] for i in range(self.number_of_buckets)]

    def __init__(self):
        self.number_of_buckets = 8 
        self._create_empty_storage()
        self.max_chain_size = 5
    
    def get_idx(self, key):
        return hash(key) % self.number_of_buckets
    
    def rehash(self):
        _storage = copy.deepcopy(self.storage)
        self.number_of_buckets *= 2
        self._create_empty_storage()
        for backet in _storage:
            for pair in backet:
                self._insert_no_rehash(pair[0], pair[1])
        del _storage
        gc.collect()

    def __setitem__(self, key, value):
        idx = self.get_idx(key)
        
        for pair in self.storage[idx]:
            if pair[0] == key:
                pair[1] = value
                return
        # not replacement
        if len(self.storage[idx]) < self.max_chain_size:
            self.storage[idx].append([key, value]) 
        else:
            self.rehash()
            self.__setitem__(key, value)

    def _insert_no_rehash(self, key, value):
        """Вставка ключа без триггера rehash, используется внутри rehash."""
        idx = self.get_idx(key)
        for pair in self.storage[idx]:
            if pair[0] == key:
                pair[1] = value
                return
        self.storage[idx].append([key, value])


    def __getitem__(self, key):
        idx = self.get_idx(key)
        for pair in self.storage[idx]:
            if pair[0] == key:
                return pair[1]

    def __delitem__(self, key):
        idx = self.get_idx(key)
        for (i, pair) in enumerate(self.storage[idx]):
            if pair[0] == key:
                del self.storage[idx][i]
                return
        raise KeyError(f"No such key: {key}")


    def keys(self):
        return [pair[0] for bucket in self.storage for pair in bucket]


    def values(self):
        return [pair[1] for bucket in self.storage for pair in bucket]

m = HashMap()
n = 1000
# вставка
start = time.time()
for i in range(n):
    m[i] = i
insert_time = time.time() - start

# поиск
start = time.time()
for i in range(n):
    assert m[i] == i
lookup_time = time.time() - start

# для сравнения, поиск в списке
lst = [[i, i] for i in range(n)]
start = time.time()
for i in range(n):
    # поиск по списку
    val = next(pair[1] for pair in lst if pair[0] == i)
    assert val == i
list_lookup_time = time.time() - start

print(f"HashMap insert: {insert_time:.4f}s, lookup: {lookup_time:.4f}s, list lookup: {list_lookup_time:.4f}s")
# Проверяем, что поиск в HashMap быстрее, чем в списке
assert lookup_time < list_lookup_time