from functools import wraps


def tracer(func):
    stack = 0
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal stack
        print(f"level: {stack}, {(func, args, kwargs)}")
        old_stack = stack
        stack += 1
        result = func(*args, **kwargs)

        def generator_wrapper(gen):
            for value in gen:
                yield value
            print(f"exit, level: {old_stack}, {gen}")
            stack_decrement()

        def stack_decrement():
            nonlocal stack
            stack -= 1

        if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
            return generator_wrapper(result)
        else:
            print(f"exit, level: {old_stack}, {result}")
            stack_decrement()
            return result
    return wrapper


@tracer
def factorial(n, f=1):
    if n <= 0:
        return f
    else:
        return factorial(n - 1, f*n)
