from tracer.main import tracer

@tracer
def permute(nums: list[int], permutation=[]):
    for (i, num) in enumerate(nums):
        yield from permute(nums[:i]+nums[i+1:], permutation+[num])
    if nums == []:
        yield permutation

def main():
    nums = list(map(int, input().split()))
    
    print(list(permute(nums)))


if __name__ == "__main__":
    main()