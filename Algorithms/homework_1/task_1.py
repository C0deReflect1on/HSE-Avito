def main():
    num = int(input())
    base = 0
    while 10**base <= num:
        base += 1
    
    start = 0
    end = base - 1
    while end > start:
        right = num // (10**end) % 10
        left = num // (10**start) % 10
        start += 1
        end -= 1
        if right != left:
            return False
    
    return True


if __name__ == "__main__":
    print(main())
