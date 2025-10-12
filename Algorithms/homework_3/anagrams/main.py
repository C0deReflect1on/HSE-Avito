from collections import defaultdict

def main():
    strs = input().split()
    
    def get_empty_dict():
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        return {i: 0 for i in alphabet}

    groups = defaultdict(list)
    for string in strs:
        str_d = get_empty_dict()
        for ch in string:
            str_d[ch] += 1
        groups[tuple(str_d.values())].append(string)

    return list(groups.values())
    
    