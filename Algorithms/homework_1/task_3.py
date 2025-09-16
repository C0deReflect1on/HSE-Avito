from typing import List

class Eratosphen: # https://ru.wikipedia.org/wiki/Решето_Эратосфена
    def __init__(self, n: int):
        if n > 0:
            self.n = n
            self.arr = [True]*(n+1) # first element will be ignored
        else:
            raise Exception("Wrong input, n shouldbe > 0")
    
    def run_sieve(self) -> List[int]:
        for number in range(2, self.n+1):
            is_prime = self.arr[number]
            if is_prime:
                prime = number
                for _number in range(prime*prime, self.n+1, prime):
                    self.arr[_number] = False
        return [number for number in range(2, self.n+1) if self.arr[number]]


def main():
    n = int(input())
    eratosphen = Eratosphen(n)
    primes = eratosphen.run_sieve()
    return len(primes)

if __name__ == "__main__":
    print(main())
