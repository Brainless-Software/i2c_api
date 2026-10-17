from abc import ABC, abstractmethod
from dataclasses import dataclass

from bitstring import BitArray, Bits

from i2c_api.commands import Address, P
from i2c_api.errors import I2CError
from i2c_api.exec_results import ExecResults
from i2c_api.language import I2CTransaction
from i2c_api.log import I2CTransactionElement
from i2c_api.logger import I2CLogger


class DummyI2CLogger(I2CLogger):
    def log_message(self, message: list[I2CTransactionElement]):
        pass


@dataclass(frozen=True, slots=True)
class RegisterAddress:
    address: int
    bus_width_in_bytes: int


class I2CMaster(ABC):
    def __init__(self, logger: I2CLogger | None = None):
        self.__logger: I2CLogger = DummyI2CLogger() if logger is None else logger

    @staticmethod
    def __pad_up_to_bytes(data: BitArray, num_bytes: int | None) -> BitArray:
        if num_bytes is None:
            if data.len % 8 != 0:
                data.prepend(BitArray(8 - data.len % 8))
            return data
        elif data.len <= num_bytes * 8:
            data.prepend(BitArray(num_bytes * 8 - data.len))
            return data
        else:
            raise ValueError(f"Input bit array is larger then pad_up_to_num_bytes={num_bytes}")

    @staticmethod
    def mk_payload(data: Bits | str | int | list[int], pad_up_to_num_bytes: int | None = None) -> BitArray:
        """
        Creates BitArray to be used as a payload in i2c write operations from `data` argument.
        If `pad_up_to_num_bytes` is None, then returned value will be padded to the next nearest number of bytes to
        ensure that returned value is integer multiple of 8 bits.

        If data is str then pass, then construct BitArray(data). For example, you can pass "`0b10010`" as a string.
        If data is Bits, then simply wrap it in BitArray.
        If data is int, then it is interpreted as unsigned value of one byte
        if data is list[int], then that is assumed to be a list of bytes.
        """
        if isinstance(data, int):
            return I2CMaster.__pad_up_to_bytes(BitArray(f"uint:8={data}"), pad_up_to_num_bytes)
        elif isinstance(data, list):
            return I2CMaster.__pad_up_to_bytes(BitArray("".join([f"uint:8={a}," for a in data])), pad_up_to_num_bytes)
        elif isinstance(data, (str, Bits)):
            return I2CMaster.__pad_up_to_bytes(BitArray(data), pad_up_to_num_bytes)
        else:
            raise TypeError("Invalid payload type")

    def logger(self) -> I2CLogger:
        return self.__logger

    def write(
        self,
        address: int,
        data: Bits | str | int | list[int],
        num_bytes: int | None = None,
    ) -> bool:
        """
        Performs write transaction sending `data` to the target device identified by `address`. At the end master will
        issue Stop condition and will release the clock line.

        :param address: i2c address of the target device
        :param data: array of bits to send to the target device; if int or list[int], then these are assumed to be bytes
        :param num_bytes: number of bytes to send or if None, then send all bits in `data` padded with zero bits to fit
            payload into fixed number of bytes. Raises ValueError if num_bytes is not None and is less than data width.
        :return: True or False indicating if write succeeded, which is that client responded with ACK bits.
        """
        log_msg = []
        try:
            return self._write(
                address,
                data=data,
                num_bytes=num_bytes,
                log_msg=log_msg,
                end_with_stop=True,
                start_with_restart=False,
            )
        finally:
            self.logger().log_message(log_msg)

    @abstractmethod
    def _write(
        self,
        address: int,
        *,
        data: Bits | str | int | list[int],
        log_msg: list[I2CTransactionElement],
        num_bytes: int | None,
        end_with_stop: bool,
        start_with_restart: bool,
    ) -> bool:
        pass

    @abstractmethod
    def _read(
        self,
        address: int,
        *,
        num_bytes: int,
        log_msg: list[I2CTransactionElement],
        end_with_stop: bool,
        start_with_restart: bool,
    ) -> Bits | None:
        pass

    def read(self, address: int, num_bytes: int = 1) -> Bits | None:
        """
        Performs read transaction reading `num_bytes` (default is 1) from the target device identified by `address`.
        At the end master will issue Stop condition and will release the clock line.

        :param address: i2c address of the target device
        :param num_bytes: number of bytes to read
        :return: None if failed to read data from the client (that is client did not send ACK bits) or data is Bits
        """
        log_msg = []
        try:
            return self._read(
                address,
                num_bytes=num_bytes,
                end_with_stop=True,
                log_msg=log_msg,
                start_with_restart=False,
            )
        finally:
            self.logger().log_message(log_msg)

    def exec(self, transaction: I2CTransaction, device_address: int = -1) -> ExecResults:
        """
        Executes I2C commands in a single transaction and returns a named tuple `ExecResults` where first value is list
        of lists of read bytes if any and second value is True or False indicating if transaction completed successfully.
        Unsuccessful completion usual means that slave device responded with NACK at some point during communication
        between master and the slave. Each sub-list within the list corresponds contiguous sequence of read bytes coming
        from the slave.
        """
        if not isinstance(transaction, I2CTransaction):
            raise I2CError("transaction argument must be instance of I2CTransactionEnd")
        elif transaction._i2c._i2c_commands == [] or not isinstance(transaction._i2c._i2c_commands[-1], P):
            raise I2CError("Unable to execute incomplete transaction")
        elif device_address == -1:
            for c in transaction._i2c._i2c_commands:
                if isinstance(c, Address) and c.address == -1:
                    raise ValueError(
                        "Some Address(...) commands are given without the address. "
                        "Thus, argument `address` must be provided."
                    )
        else:
            return self._exec(transaction, device_address)

    @abstractmethod
    def _exec(self, transaction: I2CTransaction, device_address: int = -1) -> ExecResults:
        pass

    def read_register(
        self,
        address: int,
        register: RegisterAddress,
        num_bytes: int = 1,
        use_restart: bool = True,
    ) -> Bits | None:
        """
        Reads register from the target device identified by `address`. This is a compound operation where we
        send first `write(address, register, num_bytes=1)` followed by `read(address, register, num_bytes)`.
        If `use_restart` is True (default), then if device supports it i2c restart will be used between read and write
        operations and if device does not support it them RuntimeError will be raised. if `use_restart` is False, then
        two separate transactions will be used to perform register read operation with clock line being released between
        them.

        :param address: i2c address of the target device
        :param register: address of the register to read
        :param num_bytes: number of bytes to read; this should match length of the register
        :param use_restart: True or False (default) indicating if we should try using I2C restart op between read and
                write operations
        :return: None if at any point during these transactions client sends NACK or actual Bits holding response data
        """
        if address < 0:
            raise I2CError("Invalid i2c device address")

        log_msg = []
        try:
            write_success = self._write(
                address,
                data=BitArray(f"uint:{8 * register.bus_width_in_bytes}={register.address}"),
                log_msg=log_msg,
                num_bytes=register.bus_width_in_bytes,
                end_with_stop=(not use_restart),
                start_with_restart=False,
            )
            if write_success:
                return self._read(
                    address,
                    num_bytes=num_bytes,
                    log_msg=log_msg,
                    end_with_stop=True,
                    start_with_restart=use_restart,
                )
            else:
                return None
        finally:
            self.__logger.log_message(log_msg)

    def write_register(
        self,
        address: int,
        register: RegisterAddress,
        data: Bits | str | int | list[int],
        num_bytes: int | None = None,
        read_back: bool = False,
        use_restart: bool = True,
    ) -> Bits | None:
        """
        Writes register to the target device. This is basically same as `write(...)` where first write byte is register
        address and subsequent bytes are values to write into a register.

        :param address: i2c address of the target device
        :param register: address of the register to write to
        :param data: array of bits to send to the target device; if int or list[int], then these are assumed to be
            bytes. It can be empty list which means that i2c transaction will include only register address/command.
        :param num_bytes: number of bytes to send or if None, then send all bits in `data` padded with zero bits to fit
            payload into fixed number of bytes. Raises ValueError if num_bytes is not None and is less than data width.
        :param read_back: if True, then register read operation will be performed at the end and its value returned.
            Otherwise, if False (default), then just do write and return back to the user the same BitArray that was
            supplied to this function as `data`.
        :param use_restart: True or False (default) indicating if we should try using I2C restart op between write and
            read operations. This value is applicable only of `read_back` is `True`.
        :return: Value written into the register or None if NACK was received at any moment from the client device
            including when performing readback or any other reason that i2c driver failed. Which means that write into
            register might be a success but readback fail and thus None be returned.
        """
        if address < 0:
            raise I2CError("Invalid i2c device address")

        log_msg = []
        try:
            register_value = I2CMaster.mk_payload(data, num_bytes)
            value_num_bytes = int(register_value.len / 8)
            write_success = self._write(
                address,
                data=BitArray(f"uint:{8 * register.bus_width_in_bytes}={register.address}") + register_value,
                log_msg=log_msg,
                num_bytes=(value_num_bytes + register.bus_width_in_bytes),
                end_with_stop=True,
                start_with_restart=False,
            )
            if not write_success:
                return None
            elif not read_back:
                return register_value
            else:  # read it back
                write_success = self._write(
                    address,
                    data=BitArray(f"uint:{8 * register.bus_width_in_bytes}={register.address}"),
                    log_msg=log_msg,
                    num_bytes=register.bus_width_in_bytes,
                    end_with_stop=(not use_restart),
                    start_with_restart=False,
                )
                if write_success:
                    return self._read(
                        address,
                        num_bytes=value_num_bytes,
                        log_msg=log_msg,
                        end_with_stop=True,
                        start_with_restart=use_restart,
                    )
                else:
                    return None
        finally:
            self.logger().log_message(log_msg)

    @abstractmethod
    def scan(self) -> list[int]:
        """
        Scans for all client devices connected on this I2C bus.

        :return: list of addresses of connected devices
        """

    @abstractmethod
    def list_pullups(self) -> list[str]:
        """
        Returns list of possible configurable pullup resistor values.
        These should be human-readable values like [20 OHm]
        """

    @abstractmethod
    def set_pullup(self, pullup_value: str) -> None:
        """
        Set pullup resistor value. This should be one of the strings returned by `list_pullups()` method.
        """

    @abstractmethod
    def get_pullup(self) -> str:
        """
        Returns currently active pullup resistor value in human-readable format.
        """

    @abstractmethod
    def list_clk_speeds(self) -> list[int]:
        """Returns list of available configuable clock speeds in KHz."""

    @abstractmethod
    def get_clk_speed(self) -> int:
        """Returns currently configued clock speed in KHz."""

    @abstractmethod
    def set_clk_speed(self, speed: int) -> None:
        """
        Sets clock speed to `speed` value in KHz. Supplied value must be one of the returned one by
        method `list_clk_speeds()`, if not, then RuntimeError is raised.
        """
