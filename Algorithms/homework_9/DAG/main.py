

def dfs(v, graph, visited, path, path_list, loops, topo_order):
    visited.add(v)
    path.add(v)
    path_list.append(v)


    for n in graph[v]:
        if n in path:
            idx = path_list.index(n)
            cycle = path_list[idx:] + [n]
            return cycle
            # loops.append(cycle)
        elif n not in visited:
            cycle = dfs(n, graph, visited, path, path_list, loops, topo_order)
            if cycle:
                return cycle
    # Если мы сюда попали - значит dfs дошел до конца (так-как это рекурсивно, то remove v вызовется на всем пути)
    path.remove(v)
    path_list.pop()
    topo_order.append(v)


def find_loop(graph):
    visited = set()
    path_list = []
    loops = []
    topo_order = []
    path = set()
    for node in graph.keys():
            if node not in visited:
                cycle = dfs(node, graph, visited, path, path_list, loops, topo_order)
                if cycle:
                    return ("has loop:", cycle)
    return ("topo:", topo_order[::-1])


def main():
    graph = {
        1: [2, 3],
        2: [],
        3: [4],
        4: [5, 6],
        5: [],
        6: []
    }

    print(find_loop(graph))

if __name__ == "__main__":
    main()