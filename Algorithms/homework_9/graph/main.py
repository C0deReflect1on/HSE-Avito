from collections import deque


def bfs(graph, vertex, visited):
    component = []
    queue = deque([vertex])
    visited.add(vertex)
    
    while queue:
        node = queue.popleft()
        component.append(node)
        
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    
    return component


def find_connected_components(graph):
    visited = set()
    components = []
    
    for node in graph.keys():
        if node not in visited:
            components.append(bfs(graph, node, visited))
    
    return components



def main():
    graph = {
        1: [2, 3],
        2: [1],
        3: [1],
        4: [5],
        5: [4]
    }
    print(find_connected_components(graph))


if __name__ == "__main__":
    main()
