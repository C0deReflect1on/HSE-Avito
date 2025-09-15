def main():
    nums = list(map(int, input().split()))

    sum = 0
    even_sum = 0
    even_cnt = 0
    min_even = float("+inf")
    for num in nums:
        if num % 2 == 0:
            sum += num
        else:
            even_cnt += 1
            if num < min_even:
                min_even = num
            even_sum += num
    
    sum += even_sum
    if even_cnt % 2 != 0:
        sum -= min_even

    return sum


if __name__ == "__main__":  
    print(main())