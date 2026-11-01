from dataclasses import dataclass
from typing import Callable, Optional

from i2c_api.master import DummyI2CMaster, I2CLogger, I2CMaster


@dataclass(frozen=True)
class I2CMasterProvider:
    make: str
    model: str
    new_i2c_master: Callable[[str, I2CLogger], I2CMaster]
    ports_required: bool
    list_ports: Callable[[], Optional[list[str]]] = lambda: None

    def make_and_model(self):
        return self.make + " :: " + self.model


I2CMasterProviderDummy = I2CMasterProvider(
    make="Demo",
    model="DummyI2CDongle",
    new_i2c_master=lambda port, logger: DummyI2CMaster(port, logger),
    ports_required=False,
)
