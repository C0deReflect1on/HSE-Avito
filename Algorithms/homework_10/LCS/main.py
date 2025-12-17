
def lcs(s1 ,s2):
    s1 = " " + s1
    s2 = " " + s2

    len1, len2 = len(s1), len(s2)

    # Создаем таблицу dp
    dp = [[0] * len2 for _ in range(len1)]

    # Заполнение таблицы
    for i in range(1, len1):
        for j in range(1, len2):
            if s1[i] == s2[j]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    # Восстановление LCS
    i, j = len1 - 1, len2 - 1
    lcs = []
    while i > 0 and j > 0:
        if s1[i] == s2[j]:
            lcs.append(s1[i])
            i -= 1
            j -= 1
        elif dp[i-1][j] > dp[i][j-1]:
            i -= 1
        else:
            j -= 1

    lcs = ''.join(reversed(lcs))
    return lcs


def main():
    text = "AGGTAB"
    pattern = "GXTXAYB"

    print(lcs(text, pattern))

if __name__ == "__main__":
    main()
