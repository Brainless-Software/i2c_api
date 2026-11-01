from .exec_results import ExecResults
from .language import I2CTransaction, I2CTransactionBuilder
from .log import I2CMessage
from .logger import I2CLogger
from .master import I2CMaster, RegisterAddress
from .provider import I2CMasterProvider

I2CAPI_IMPL: list[I2CMasterProvider] = [provider.I2CMasterProviderDummy]
