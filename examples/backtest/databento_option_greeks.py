# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## imports

# %%
# Note: Use the python extension jupytext to be able to open this python file in jupyter as a notebook

# %%
import pandas as pd

from nautilus_trader.adapters.databento.data_utils import data_path
from nautilus_trader.adapters.databento.data_utils import databento_data
from nautilus_trader.adapters.databento.data_utils import load_catalog
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.config import BacktestRunConfig
from nautilus_trader.config import BacktestVenueConfig
from nautilus_trader.config import ImportableActorConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.config import StreamingConfig
from nautilus_trader.core.datetime import unix_nanos_to_iso8601
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import DataType
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.greeks_data import GreeksData
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.persistence.config import DataCatalogConfig
from nautilus_trader.persistence.loaders import InterestRateProvider
from nautilus_trader.persistence.loaders import InterestRateProviderConfig
from nautilus_trader.trading.strategy import Strategy


# %% [markdown]
# ## parameters

# %%
# Set the data path for Databento data
# import nautilus_trader.adapters.databento.data_utils as db_data_utils
# DATA_PATH = "/path/to/your/data"  # Use your own value here
# db_data_utils.DATA_PATH = DATA_PATH

catalog_folder = "options_catalog"
catalog = load_catalog(catalog_folder)

future_symbols = ["ESM4"]
option_symbols = ["ESM4 P5230", "ESM4 P5250"]

# small amount of data to download for testing, very cheap
# Note that the example below doesn't need any download as the test data is included in the repository
start_time = "2024-05-09T10:00"
end_time = "2024-05-09T10:05"

# A valid databento key can be entered here (or as an env variable of the same name)
# DATABENTO_API_KEY = None
# db_data_utils.init_databento_client(DATABENTO_API_KEY)

# https://databento.com/docs/schemas-and-data-formats/whats-a-schema
futures_data = databento_data(
    future_symbols,
    start_time,
    end_time,
    "ohlcv-1m",
    "futures",
    catalog_folder,
)
options_data = databento_data(
    option_symbols,
    start_time,
    end_time,
    "bbo-1m",
    "options",
    catalog_folder,
)


# %% [markdown]
# ## strategy


# %%
class OptionConfig(StrategyConfig, frozen=True):
    future_id: InstrumentId
    option_id: InstrumentId
    option_id2: InstrumentId
    load_greeks: bool = False


class OptionStrategy(Strategy):
    """
    An options trading strategy that calculates and displays the portfolio greeks.

    The strategy subscribes to quotes for two options and a futures contract, and
    initializes a portfolio with some trades. It can optionally load greeks from a
    catalog, or compute them on the fly. The strategy logs the portfolio greeks at
    regular intervals.

    """

    def __init__(self, config: OptionConfig):
        super().__init__(config=config)
        self.start_orders_done = False

    def on_start(self):
        self.bar_type = BarType.from_str(f"{self.config.future_id}-1-MINUTE-LAST-EXTERNAL")

        self.request_instrument(self.config.option_id)
        self.request_instrument(self.config.option_id2)
        self.request_instrument(self.bar_type.instrument_id)

        self.subscribe_quote_ticks(
            self.config.option_id,
            params={"duration_seconds": pd.Timedelta(minutes=2).seconds},
        )
        self.subscribe_quote_ticks(self.config.option_id2)
        self.subscribe_bars(self.bar_type)

        self.subscribe_data(
            DataType(GreeksData),
            instrument_id=self.config.option_id,
            params={
                "append_data": False,
            },  # prepending data ensures that greeks are cached and available before on_bar
        )
        self.subscribe_data(
            DataType(GreeksData),
            instrument_id=self.config.option_id2,
            params={"append_data": False},
        )
        self.greeks.subscribe_greeks(
            InstrumentId.from_str("ES*.XCME"),
        )  # adds all ES greeks read from the message bus to the cache

    def init_portfolio(self):
        self.submit_market_order(instrument_id=self.config.option_id, quantity=-10)
        self.submit_market_order(instrument_id=self.config.option_id2, quantity=10)
        self.submit_market_order(instrument_id=self.config.future_id, quantity=1)

        self.start_orders_done = True

    # def on_data(self, greeks):
    #     self.log.warning(f"{greeks=}")
    #     self.cache.add_greeks(greeks)

    def on_bar(self, bar):
        self.user_log(
            f"bar ts_init = {unix_nanos_to_iso8601(bar.ts_init)}, bar close = {bar.close}",
        )

        if not self.start_orders_done:
            self.user_log("Initializing the portfolio with some trades")
            self.init_portfolio()
            return

        self.display_greeks()

    def display_greeks(self, alert=None):
        portfolio_greeks = self.greeks.portfolio_greeks(
            use_cached_greeks=self.config.load_greeks,
            publish_greeks=(not self.config.load_greeks),
            # underlyings=["ES"],
            # spot_shock=10.,
            # vol_shock=0.0,
            # percent_greeks=True,
            # index_instrument_id=self.config.future_id,
            # beta_weights={self.config.future_id: 2.}
        )
        self.user_log(f"{portfolio_greeks=}")

    def submit_market_order(self, instrument_id, quantity):
        order = self.order_factory.market(
            instrument_id=instrument_id,
            order_side=(OrderSide.BUY if quantity > 0 else OrderSide.SELL),
            quantity=Quantity.from_int(abs(quantity)),
        )

        self.submit_order(order)

    def submit_limit_order(self, instrument_id, price, quantity):
        order = self.order_factory.limit(
            instrument_id=instrument_id,
            order_side=(OrderSide.BUY if quantity > 0 else OrderSide.SELL),
            quantity=Quantity.from_int(abs(quantity)),
            price=Price(price),
        )

        self.submit_order(order)

    def user_log(self, msg):
        self.log.warning(str(msg), color=LogColor.GREEN)

    def on_stop(self):
        self.unsubscribe_bars(self.bar_type)
        self.unsubscribe_quote_ticks(self.config.option_id)
        self.unsubscribe_quote_ticks(self.config.option_id2)
        self.unsubscribe_data(DataType(GreeksData), instrument_id=self.config.option_id)
        self.unsubscribe_data(DataType(GreeksData), instrument_id=self.config.option_id2)


# %% [markdown]
# ## backtest node

# %%
# BacktestEngineConfig

# When load_greeks is False, the streamed greeks can be saved after the backtest
# When load_greeks is True, the greeks are loaded from the catalog
load_greeks = False

actors = [
    ImportableActorConfig(
        actor_path=InterestRateProvider.fully_qualified_name(),
        config_path=InterestRateProviderConfig.fully_qualified_name(),
        config={
            "interest_rates_file": str(data_path(catalog_folder, "usd_short_term_rate.xml")),
        },
    ),
]

strategies = [
    ImportableStrategyConfig(
        strategy_path=OptionStrategy.fully_qualified_name(),
        config_path=OptionConfig.fully_qualified_name(),
        config={
            "future_id": InstrumentId.from_str(f"{future_symbols[0]}.XCME"),
            "option_id": InstrumentId.from_str(f"{option_symbols[0]}.XCME"),
            "option_id2": InstrumentId.from_str(f"{option_symbols[1]}.XCME"),
            "load_greeks": load_greeks,
        },
    ),
]

streaming = StreamingConfig(
    catalog_path=catalog.path,
    fs_protocol="file",
    include_types=[GreeksData],
)

logging = LoggingConfig(
    bypass_logging=False,
    log_colors=True,
    log_level="WARN",
    log_level_file="WARN",
    log_directory=".",
    log_file_format=None,  # "json" or None
    log_file_name="databento_option_greeks",
    clear_log_file=True,
    print_config=False,
    use_pyo3=False,
)

catalogs = [
    DataCatalogConfig(
        path=catalog.path,
    ),
]

engine_config = BacktestEngineConfig(
    logging=logging,
    actors=actors,
    strategies=strategies,
    streaming=(streaming if not load_greeks else None),
    catalogs=catalogs,
)

# BacktestRunConfig

data = [
    # # TODO using instrument_id and bar_spec only, or instrument_ids and bar_spec only, or bar_types only
    BacktestDataConfig(
        data_cls=Bar,
        catalog_path=catalog.path,
        instrument_id=InstrumentId.from_str(f"{future_symbols[0]}.XCME"),
        # instrument_ids=[InstrumentId.from_str(f"{future_symbols[0]}.XCME")],
        bar_spec="1-MINUTE-LAST",
        # bar_types=[f"{future_symbols[0]}.XCME-1-MINUTE-LAST-EXTERNAL"],
        # start_time=start_time,
        # end_time=end_time,
    ),
    BacktestDataConfig(
        data_cls=QuoteTick,
        catalog_path=catalog.path,
        # instrument_ids=[InstrumentId.from_str(f"{option_symbols[0]}.XCME"), InstrumentId.from_str(f"{option_symbols[1]}.XCME")],
    ),
]

if load_greeks:
    # Important note: when prepending custom data to usual market data, it will reach actors/strategies earlier
    data = [
        BacktestDataConfig(
            data_cls=GreeksData.fully_qualified_name(),
            catalog_path=catalog.path,
            client_id="GreeksDataProvider",
            # metadata={"instrument_id": "ES"}, # not used anymore, reminder on syntax
        ),
        *data,
    ]

venues = [
    BacktestVenueConfig(
        name="XCME",
        oms_type="NETTING",
        account_type="MARGIN",
        base_currency="USD",
        starting_balances=["1_000_000 USD"],
    ),
]

configs = [
    BacktestRunConfig(
        engine=engine_config,
        data=[],  # data
        venues=venues,
        chunk_size=None,  # use None when loading custom data, else a value of 10_000 for example
        start=start_time,
        end=end_time,
        raise_exception=True,
    ),
]

node = BacktestNode(configs=configs)

# %%
results = node.run()

# %%
if not load_greeks:
    catalog.convert_stream_to_data(
        results[0].instance_id,
        GreeksData,
    )

# %% [markdown]
# ## backtest results

# %%
engine = node.get_engine(configs[0].id)
engine.trader.generate_order_fills_report()

# %%
engine.trader.generate_positions_report()

# %%
engine.trader.generate_account_report(Venue("XCME"))

# %%
node.dispose()
