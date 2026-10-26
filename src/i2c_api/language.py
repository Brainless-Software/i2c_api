import json
from typing import Protocol

from i2c_api.commands import Address, Command, Data, P, Read, S, Sr, W
from i2c_api.exec_results import ExecResults


class I2CMaster(Protocol):
    def exec(self, transaction: "I2CTransaction", device_address: int = -1) -> ExecResults: ...

    def _exec(self, transaction: "I2CTransaction", device_address: int = -1) -> ExecResults: ...


class I2CTransaction:
    def __init__(self, i2c: "I2CTransactionBuilder"):
        self._i2c = i2c

    def __repr__(self) -> str:
        return ".".join(str(c) for c in self._i2c._i2c_commands)

    def exec(self, master: I2CMaster | None = None, device_address: int = -1) -> ExecResults:
        master = self._i2c._i2c_master if master is None else master
        device_address = self._i2c._default_device_address if device_address == -1 else device_address
        if master is None:
            raise ValueError("I2CMaster must be provided to execute this transaction")

        def get_transaction():
            if device_address == -1:
                for c in self._i2c._i2c_commands:
                    if isinstance(c, Address) and c.address == -1:
                        raise ValueError(
                            "Some Address(...) commands are given without the address. "
                            "Thus, argument `device_address` must be provided."
                        )
                return self

            else:
                # Autofill addresses if necessary.
                new_root = I2CTransactionBuilder()
                for c in self._i2c._i2c_commands:
                    if isinstance(c, Address):
                        if c.address == -1:
                            new_root._i2c_commands.append(Address(device_address))
                        else:
                            new_root._i2c_commands.append(c)
                    else:
                        new_root._i2c_commands.append(c)

                return I2CTransaction(new_root)

        return master.exec(get_transaction())

    @staticmethod
    def to_json(transaction: "I2CTransaction") -> str:
        return json.dumps([cmd.to_dict() for cmd in transaction._i2c._i2c_commands])

    @staticmethod
    def from_json(json_str: str) -> "I2CTransaction":
        i2c = I2CTransactionBuilder()
        op = ""
        payload_acc: list[int] = []
        for cmd in json.loads(json_str):
            match cmd["cmd"]:
                case "S":
                    i2c = i2c.start()
                case "Address":
                    i2c = i2c.address(int(cmd["address"]))
                case "W":
                    op = "write"
                case "Data":
                    payload_acc.append(int(cmd["payload"]))
                case "Sr":
                    if op == "write":
                        i2c = i2c.write(payload_acc)
                        op = ""
                        payload_acc.clear()
                    i2c = i2c.restart()
                case "Read":
                    i2c = i2c.read(int(cmd["num_bytes"]))
                case "P":
                    if op == "write":
                        i2c = i2c.write(payload_acc)
                    return i2c.stop()

        raise ValueError("Unable to deserialize I2C transaction from provided string")


class I2CStopStart:
    def __init__(self, i2c: "I2CTransactionBuilder"):
        self._i2c = i2c

    def stop(self) -> I2CTransaction:
        self._i2c._i2c_commands.append(P())
        return I2CTransaction(self._i2c)

    def restart(self) -> "I2CAddress":
        self._i2c._i2c_commands.append(Sr())
        return I2CAddress(self._i2c)


class I2CReadWrite:
    def __init__(self, i2c: "I2CTransactionBuilder"):
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
    def __init__(self, i2c: "I2CTransactionBuilder"):
        self._i2c = i2c

    def address(self, device_address: int = -1) -> I2CReadWrite:
        self._i2c._i2c_commands.append(Address(device_address))
        return I2CReadWrite(self._i2c)


class I2CTransactionBuilder:
    def __init__(self, i2c_master: I2CMaster | None = None, default_device_address: int = -1):
        self._i2c_commands: list[Command] = []
        self._i2c_master = i2c_master
        self._default_device_address = default_device_address

    def start(self) -> I2CAddress:
        new_root = I2CTransactionBuilder()
        new_root._i2c_commands.append(S())
        return I2CAddress(new_root)

    def __repr__(self) -> str:
        return ".".join(str(c) for c in self._i2c_commands)
