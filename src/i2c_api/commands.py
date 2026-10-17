class Command:
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def to_dict(self) -> dict[str, str]:
        return {"cmd": self.__class__.__name__}


class S(Command):
    pass


class Address(Command):
    __match_args__ = ("address",)

    def __init__(self, address: int):
        self.address = address

    def __repr__(self) -> str:
        if self.address == -1:
            return f"{self.__class__.__name__}(auto)"
        else:
            return f"{self.__class__.__name__}(0x{self.address:02X})"

    def to_dict(self) -> dict[str, str]:
        return {"cmd": self.__class__.__name__, "address": f"{self.address}"}


class Address10(Command):
    __match_args__ = ("address",)

    def __init__(self, address: int):
        self.address = address

    def __repr__(self) -> str:
        if self.address == -1:
            return f"{self.__class__.__name__}(auto)"
        else:
            return f"{self.__class__.__name__}(0x{self.address:02X})"

    def to_dict(self) -> dict[str, str]:
        return {"cmd": self.__class__.__name__, "address": f"{self.address}"}


class W(Command):
    pass


class Data(Command):
    __match_args__ = ("data",)

    def __init__(self, data: int):
        self.data = data

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(0x{self.data:02X})"

    def to_dict(self) -> dict[str, str]:
        return {"cmd": self.__class__.__name__, "payload": f"{self.data}"}


class Read(Command):
    __match_args__ = ("num_bytes",)

    def __init__(self, num_bytes: int):
        self.num_bytes = num_bytes

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.num_bytes})"

    def to_dict(self) -> dict[str, str]:
        return {"cmd": self.__class__.__name__, "num_bytes": f"{self.num_bytes}"}


class Sr(Command):
    pass


class P(Command):
    pass
