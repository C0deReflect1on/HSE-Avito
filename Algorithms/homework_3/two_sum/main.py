def main():
    arr = list(map(int, input().split()))
    k = int(input())
    match_pair = {}
    for (i, elem) in enumerate(arr):
        if (pair_idx:=match_pair.get(k-elem)) is not None:
            return min(pair_idx, i), max(pair_idx, i)
        match_pair[elem] = i

    return -1

if __name__ == "__main__":
    print(main())