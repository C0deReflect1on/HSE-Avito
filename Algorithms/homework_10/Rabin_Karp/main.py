def rolling_hash(prev_hash, s_left, s_right, p_pow, p, M):
    """
    Все очень просто, берем полиномиальный хэш:
    s_a = [s_0, s_m-1]
    s_b = [s_1, s_m]
    H(a)=(s0​⋅p^m−1+s1​⋅p^m−2+⋯+s_m−1​)modM
    H(b) = (       s1​⋅p^m−1+s2​⋅p^m−2+⋯+s_m−1*p + s_m​)modM
    Заметим, что H(b):
    H(b) = (H(a) - s0*p^{m-1})*p + s_m 
    Все конец
    """
    return ((prev_hash - ord(s_left)*p_pow)*p + ord(s_right)) % M
    

def rabin_karp(text: str, pattern: str) -> list[int]:
    n = len(text)
    m = len(pattern)

    if m == 0 or m > n:
        return []

    p = 31
    M = 10**9 + 7

    # (a mod M−b mo dM)⋅p mod M+c mod M=((a−b)∗p+c) mod M
    p_pow = 1
    for _ in range(m - 1):
        p_pow = (p_pow * p) % M

    pattern_hash = 0
    for c in pattern:
        pattern_hash = (pattern_hash * p + ord(c)) % M
    
    # Один раз посчитали

    # start
    window_hash = 0
    for i in range(m): # O(m)
        window_hash = (window_hash * p + ord(text[i])) % M

    result = []

    for i in range(len(text) - len(pattern) + 1): # n-m+1 раз прошлись по тексту
        if window_hash == pattern_hash:
            if text[i:i + m] == pattern: # O(m)
                result.append(i)

        if i+m < n:
            window_hash = rolling_hash(window_hash, text[i], text[i+m], p_pow, p, M) # O(1)

    # Вот и получается O(n-m+1) + O(m) + O(k*m) (сколько раз паттер встретился) = O(n+k*m)
    return result


def main():
    text = "abracadabra"
    pattern = "abra"

    print(rabin_karp(text, pattern))

if __name__ == "__main__":
    main()