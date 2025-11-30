import pytest
from main import dijkstra


def test_single_vertex():
    """Одна вершина"""
    graph = {'A': []}
    result = dijkstra(graph, 'A')
    assert result == {'A': 0}


def test_simple_path():
    """Линейный путь"""
    graph = {
        'A': [('B', 2)],
        'B': [('A', 2), ('C', 3)],
        'C': [('B', 3)]
    }
    result = dijkstra(graph, 'A')
    assert result == {'A': 0, 'B': 2, 'C': 5}


def test_multiple_paths():
    """Выбор кратчайшего из нескольких путей"""
    graph = {
        'A': [('B', 4), ('C', 2)],
        'B': [('A', 4), ('C', 1), ('D', 5)],
        'C': [('A', 2), ('B', 1), ('D', 8)],
        'D': [('B', 5), ('C', 8)]
    }
    result = dijkstra(graph, 'A')
    assert result['A'] == 0
    assert result['C'] == 2
    assert result['B'] == 3
    assert result['D'] == 8


def test_unreachable_vertex():
    """Недостижимая вершина"""
    graph = {
        'A': [('B', 1)],
        'B': [('A', 1)],
        'C': [('D', 1)],
        'D': [('C', 1)]
    }
    result = dijkstra(graph, 'A')
    assert result['A'] == 0
    assert result['B'] == 1
    assert result['C'] == float('inf')
    assert result['D'] == float('inf')


def test_graph_with_cycle():
    """Граф с циклом"""
    graph = {
        'A': [('B', 1)],
        'B': [('C', 2)],
        'C': [('A', 3), ('D', 1)],
        'D': [('C', 1)]
    }
    result = dijkstra(graph, 'A')
    assert result['A'] == 0
    assert result['B'] == 1
    assert result['C'] == 3
    assert result['D'] == 4


def test_diamond_graph():
    """Граф-ромб (два пути разной длины)"""
    graph = {
        'A': [('B', 1), ('C', 10)],
        'B': [('D', 1)],
        'C': [('D', 1)],
        'D': []
    }
    result = dijkstra(graph, 'A')
    assert result['A'] == 0
    assert result['B'] == 1
    assert result['D'] == 2
    assert result['C'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
