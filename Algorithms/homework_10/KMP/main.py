from typing import List

def prefix_builder(s: str) -> List[int]:
    m = len(s)
    prefix = [0 for i in range(m)]
    j = 0
    for i in range(1, m):
        while j > 0 and s[i] != s[j]:
            j = prefix[j-1]
        if s[i] == s[j]:
            j += 1
        prefix[i] = j
    return prefix


def kmp_search(text, pattern) -> List[int]:
    print(text, pattern)
    prefix_store = prefix_builder(pattern)
    j = 0
    i = 0
    occurrences = []
    if len(pattern) == 0:
        return []
    while i < len(text):
        print(i, j)
        if text[i] == pattern[j]:
            j += 1
            i += 1
        else:
            if j > 0:
                j = prefix_store[j-1]
            else:
                j = 0
                i += 1 
        if j == len(pattern):
            occurrences.append(i - len(pattern))
            j = prefix_store[j-1]
    return occurrences

def main():
    text = "abracadabra"
    pattern = "abra"

    print(kmp_search(text, pattern))

if __name__ == "__main__":
    main()
