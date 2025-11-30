import pytest
from main import find_loop


def test_dag_returns_topo_order():
    """DAG → топологический порядок"""
    graph = {1: [2], 2: [3], 3: []}
    result = find_loop(graph)
    assert result[0] == "topo:"
    assert result[1] == [1, 2, 3]


def test_cycle_detected():
    """Цикл → возвращает цикл"""
    graph = {1: [2], 2: [3], 3: [1]}
    result = find_loop(graph)
    assert result[0] == "has loop:"
    assert result[1] == [1, 2, 3, 1]


def test_self_loop():
    """Петля → цикл из одной вершины"""
    graph = {1: [1]}
    result = find_loop(graph)
    assert result[0] == "has loop:"
    assert result[1] == [1, 1]


def test_empty_graph():
    """Пустой граф"""
    graph = {}
    result = find_loop(graph)
    assert result == ("topo:", [])


def test_cycle_not_from_start():
    """Цикл не от стартовой вершины: 1 → 2 → 3 → 2"""
    graph = {1: [2], 2: [3], 3: [2]}
    result = find_loop(graph)
    assert result[0] == "has loop:"
    assert result[1] == [2, 3, 2]  # цикл без 1
