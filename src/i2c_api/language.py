from typing import Protocol

from i2c_api.commands import Address, Command, Data, P, Read, S, Sr, W
from i2c_api.exec_results import ExecResults


class I2CMaster(Protocol):
    def exec(self, transaction: "I2CTransactionEnd") -> ExecResults: ...

    def _exec(self, transaction: "I2CTransactionEnd") -> ExecResults: ...


class I2CTransactionEnd:
    def __init__(self, i2c: "I2CTransaction"):
        self._i2c = i2c

    def __repr__(self) -> str:
        return "i2c." + ".".join(str(c) for c in self._i2c._i2c_commands)

    def exec(self, master: I2CMaster | None = None, device_address: int = -1) -> ExecResults:
        if self._i2c._master is None and master is None:
            raise ValueError("I2CMaster must be provided to execute this transaction")

        if device_address == -1:
            device_address = self._i2c._default_device_address

        def get_transaction():
            if device_address == -1:
                for c in self._i2c._i2c_commands:
                    if isinstance(c, Address) and c.address == -1:
                        raise ValueError(
                            "Some Address(...) commands are given without address. "
                            "Thus, argument `address` must be provided."
                        )
                return self

            else:
                # Autofill addresses if necessary.
                new_root = I2CTransaction(self._i2c._master, self._i2c._default_device_address)
                new_root._master = self._i2c._master
                for c in self._i2c._i2c_commands:
                    if isinstance(c, Address):
                        if c.address == -1:
                            new_root._i2c_commands.append(Address(device_address))
                        else:
                            new_root._i2c_commands.append(c)
                    else:
                        new_root._i2c_commands.append(c)

                return new_root

        master_to_use = self._i2c._master if master is None else master
        return master_to_use.exec(get_transaction())


class I2CStopStart:
    def __init__(self, i2c: "I2CTransaction"):
        self._i2c = i2c

    def stop(self) -> I2CTransactionEnd:
        self._i2c._i2c_commands.append(P())
        return I2CTransactionEnd(self._i2c)

    def restart(self) -> "I2CAddress":
        self._i2c._i2c_commands.append(Sr())
        return I2CAddress(self._i2c)


class I2CReadWrite:
    def __init__(self, i2c: "I2CTransaction"):
        self._i2c = i2c

    def read(self, number_of_bytes: int) -> I2CStopStart:
        self._i2c._i2c_commands.append(Read(number_of_bytes))
        return I2CStopStart(self._i2c)

    def write(self, data: int | list[int]) -> I2CStopStart:
        self._i2c._i2c_commands.append(W())
        if isinstance(data, int):
            self._i2c._i2c_commands.append(Data(data))
        else:
            for b in data:
                self._i2c._i2c_commands.append(Data(b))
        return I2CStopStart(self._i2c)


class I2CAddress:
    def __init__(self, i2c: "I2CTransaction"):
        self._i2c = i2c

    def address(self, device_address: int = -1) -> I2CReadWrite:
        self._i2c._i2c_commands.append(Address(device_address))
        return I2CReadWrite(self._i2c)

    def address10(self, device_address: int = -1) -> I2CReadWrite:
        raise RuntimeError("Not implemented")


class I2CTransaction:
    def __init__(self, master: I2CMaster | None = None, default_device_address: int = -1):
        self._master = master
        self._default_device_address = default_device_address
        self._i2c_commands: list[Command] = []

    def start(self) -> I2CAddress:
        new_root = I2CTransaction(self._master, self._default_device_address)
        new_root._i2c_commands.append(S())
        return I2CAddress(new_root)

    def __repr__(self) -> str:
        return "i2c." + ".".join(str(c) for c in self._i2c_commands)
