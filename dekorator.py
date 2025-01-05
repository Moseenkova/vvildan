def decorator(func):
    def duda(*args, **kwargs):
        print("start")
        result = func(*args, **kwargs)
        print("finish")
        return result

    return duda


@decorator
def add_one(a):
    print(a + 1)


add_one(1)
