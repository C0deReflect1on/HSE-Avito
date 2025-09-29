def main():
    pushed = input().split()
    poped = input().split()

    # так как числа уникальные, то идем push до первого совпадения с целевым poped

    stack = []
    i_pushed = 0
    i_poped = 0
    while i_pushed < len(pushed):
        if len(stack) > 0 and stack[-1] == poped[i_poped]:
            stack.pop()
            i_poped += 1
        else:
            stack.append(pushed[i_pushed])
            i_pushed += 1

    while i_poped < len(poped):
        if stack[-1] == poped[i_poped]:
            stack.pop()
            i_poped += 1
        else:
            return False
    
    return True

if __name__ == "__main__":
    print(main())
