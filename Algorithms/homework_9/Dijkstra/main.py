import heapq


def dijkstra(graph, start):
    distances = {vertex: float('inf') for vertex in graph}
    distances[start] = 0
    
    pq = []
    heapq.heappush(pq, (0, start))
    visited = set()
    
    while pq:
        curr_dst, curr_vertex = heapq.heappop(pq)

        if curr_vertex in visited:
            continue
        visited.add(curr_vertex)
        
        for neighbor, weight in graph[curr_vertex]:
            distance = curr_dst + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                heapq.heappush(pq, (distance, neighbor))

    return distances

def main():
    graph = {
        'A': [('B', 4), ('C', 2)],
        'B': [('A', 4), ('C', 1), ('D', 5)],
        'C': [('A', 2), ('B', 1), ('D', 8)],
        'D': [('B', 5), ('C', 8)]
    }
    
    distances = dijkstra(graph, 'A')
    
    for vertex, distance in distances.items():
        print(f"Расстояние от A до {vertex}: {distance}")

if __name__ == "__main__":
    main()