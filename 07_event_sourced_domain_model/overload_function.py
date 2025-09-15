from functools import singledispatch

@singledispatch
def show(value):
    raise TypeError("Unsupported type")

@show.register
def _(value: int):
    print(f"int: {value}")

@show.register
def _(value: str):
    print(f"str: {value}")


if __name__ == "__main__":
    show(42)      # int: 42
    show("hello") # str: hello