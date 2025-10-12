import pytest
import time
from copy import deepcopy
from main import HashMap

@pytest.fixture
def empty_map():
    return HashMap()


def test_set_and_get(empty_map):
    empty_map["a"] = 1
    empty_map["b"] = 2
    empty_map["c"] = 3
    assert empty_map["a"] == 1
    assert empty_map["b"] == 2
    assert empty_map["c"] == 3


def test_update_value(empty_map):
    empty_map["x"] = 10
    empty_map["x"] = 20
    assert empty_map["x"] == 20


def test_delete(empty_map):
    empty_map["k"] = 100
    del empty_map["k"]
    with pytest.raises(KeyError):
        _ = empty_map["k"]


def test_keys_values(empty_map):
    empty_map["a"] = 1
    empty_map["b"] = 2
    keys = empty_map.keys()
    values = empty_map.values()
    assert set(keys) == {"a", "b"}
    assert set(values) == {1, 2}


def test_rehashing():
    # маленький max_chain_size, чтобы триггерить рехеш
    m = HashMap()
    m.max_chain_size = 1
    for i in range(10):
        m[i] = i * 10
    # проверяем, что все элементы доступны после rehash
    for i in range(10):
        assert m[i] == i * 10
    # проверяем, что number_of_buckets увеличилось
    assert m.number_of_buckets > 8


def test_performance():
    m = HashMap()
    n = 100
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


def test_update_existing_key():
    m = HashMap()
    m["a"] = 1
    m["a"] = 42  # обновляем существующий ключ
    assert m["a"] == 42
    # вставим ещё один ключ, чтобы убедиться, что остальные не затёрты
    m["b"] = 7
    assert m["b"] == 7
    assert m["a"] == 42


def test_bucket_collisions():
    m = HashMap()
    
    keys = list(range(10))
    for k in keys:
        m[k] = k * 10

    m.number_of_buckets = 5
    m.max_chain_size = 2

    old_bucket_count = m.number_of_buckets
    old_storage = deepcopy(m.storage)

    for k in range(10, 11): # по дирихле делаем rehash
        m[k] = k * 10

    # number_of_buckets должно увеличиться
    assert m.number_of_buckets > old_bucket_count
    del m[10]
    assert m.storage != old_storage
    # Проверяем, что ни один бакет не переполнен
    for bucket in m.storage:
        assert len(bucket) <= m.max_chain_size

    # Проверяем, что все значения доступны
    for k in range(10):
        assert m[k] == k * 10

