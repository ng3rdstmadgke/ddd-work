from pydantic import BaseModel, PrivateAttr

class A(BaseModel):
    a: int
    b: int
    c: int
    d: int
    e: int

class B(BaseModel):
    a: int
    d: int

    @property
    def b(self) -> int:
        return self.a // 2

    @property
    def c(self) -> int:
        return self.a // 3
    
    @property
    def e(self) -> int:
        return self.d * 2

if __name__ == "__main__":
    b = B(a=6, d=10)
    print(b.a)  # 6
    print(b.b)  # 3
    print(b.c)  # 2
    print(b.d)  # 10
    print(b.e)  # 20