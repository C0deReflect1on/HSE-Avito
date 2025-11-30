import pytest
from main import find_connected_components


def test_empty_graph():
    """Тест: пустой граф"""
    graph = {}
    result = find_connected_components(graph)
    assert result == []


def test_single_vertex_no_edges():
    """Тест: одна изолированная вершина"""
    graph = {1: []}
    result = find_connected_components(graph)
    assert result == [[1]]


def test_multiple_isolated_vertices():
    """Тест: несколько изолированных вершин"""
    graph = {
        1: [],
        2: [],
        3: []
    }
    result = find_connected_components(graph)
    # Каждая вершина — отдельная компонента
    assert len(result) == 3
    assert [1] in result
    assert [2] in result
    assert [3] in result


def test_fully_connected_graph():
    """Тест: полностью связный граф (одна компонента)"""
    graph = {
        1: [2, 3],
        2: [1, 3],
        3: [1, 2]
    }
    result = find_connected_components(graph)
    assert len(result) == 1
    assert set(result[0]) == {1, 2, 3}


def test_two_separate_components():
    """Тест: две отдельные компоненты"""
    graph = {
        1: [2, 3],
        2: [1],
        3: [1],
        4: [5],
        5: [4]
    }
    result = find_connected_components(graph)
    assert len(result) == 2
    
    # Сортируем компоненты для устойчивости теста
    result_sorted = [sorted(comp) for comp in result]
    assert [1, 2, 3] in result_sorted
    assert [4, 5] in result_sorted


def test_three_components_with_isolated():
    """Тест: три компоненты, включая изолированную вершину"""
    graph = {
        1: [2],
        2: [1],
        3: [4],
        4: [3],
        5: []
    }
    result = find_connected_components(graph)
    assert len(result) == 3
    
    result_sorted = [sorted(comp) for comp in result]
    assert [1, 2] in result_sorted
    assert [3, 4] in result_sorted
    assert [5] in result_sorted


def test_linear_graph():
    """Тест: линейный граф (цепочка)"""
    graph = {
        1: [2],
        2: [1, 3],
        3: [2, 4],
        4: [3]
    }
    result = find_connected_components(graph)
    assert len(result) == 1
    assert set(result[0]) == {1, 2, 3, 4}


def test_graph_with_cycle():
    """Тест: граф с циклом"""
    graph = {
        1: [2, 3],
        2: [1, 3],
        3: [1, 2, 4],
        4: [3]
    }
    result = find_connected_components(graph)
    assert len(result) == 1
    assert set(result[0]) == {1, 2, 3, 4}
    # Проверка: каждая вершина встречается ровно 1 раз
    assert len(result[0]) == 4


def test_star_graph():
    """Тест: граф-звезда (одна центральная вершина)"""
    graph = {
        1: [2, 3, 4, 5],
        2: [1],
        3: [1],
        4: [1],
        5: [1]
    }
    result = find_connected_components(graph)
    assert len(result) == 1
    assert set(result[0]) == {1, 2, 3, 4, 5}


def test_complete_graph():
    """Тест: полный граф (все соединены со всеми)"""
    graph = {
        1: [2, 3, 4],
        2: [1, 3, 4],
        3: [1, 2, 4],
        4: [1, 2, 3]
    }
    result = find_connected_components(graph)
    assert len(result) == 1
    assert set(result[0]) == {1, 2, 3, 4}


def test_no_duplicates_in_components():
    """Тест: проверка отсутствия дубликатов вершин"""
    graph = {
        1: [2, 3],
        2: [1, 3],
        3: [1, 2]
    }
    result = find_connected_components(graph)
    
    # Проверяем, что нет дубликатов внутри компонент
    for component in result:
        assert len(component) == len(set(component))
    
    # Проверяем, что нет дубликатов между компонентами
    all_vertices = []
    for component in result:
        all_vertices.extend(component)
    assert len(all_vertices) == len(set(all_vertices))


def test_string_vertices():
    """Тест: вершины — строки (не только числа)"""
    graph = {
        'A': ['B', 'C'],
        'B': ['A'],
        'C': ['A'],
        'D': ['E'],
        'E': ['D']
    }
    result = find_connected_components(graph)
    assert len(result) == 2
    
    result_sorted = [sorted(comp) for comp in result]
    assert ['A', 'B', 'C'] in result_sorted
    assert ['D', 'E'] in result_sorted


def test_large_component():
    """Тест: большая компонента (проверка производительности)"""
    # Создаем граф с 100 вершинами, все связаны в одну компоненту
    graph = {i: [i-1, i+1] if 0 < i < 99 else ([1] if i == 0 else [98]) 
             for i in range(100)}
    
    result = find_connected_components(graph)
    assert len(result) == 1
    assert len(result[0]) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])