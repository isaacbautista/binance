# Binance - A Binance API written in Python3

## General Usage

To use authenticated methods, API keys are required.

Keys are not required to save historical data or to use any of the methods in
the Public classes.

The code is written to work with API keys stored as environment variables for security.

I suggest creating a keys.sh file to store your keys and running

```shell
source keys.sh
```

before using the API. Use this template file:

```shell
#!/bin/bash

################## BINANCE ##################

export BINANCE_API="-your public key-"
export BINANCE_API_SECRET="-your secret key-"
```

.sh files are .gitignored to prevent keys from being posted or tracked by .git.

## Saving Historical Data

Data is saved in the following format:

Open time, close time, open price, high price, low price, close price, volume


The Binance API supports the following intervals:

1m, 3m, 5m, 15m, 30m

1h, 2h, 4h, 6h, 8h, 12h

1d, 3d

1w

1M

Sample usage:

```python
from binance import *

binance = BinancePublic()

# symbol: XRPBTC (Ripple)
# dates: mm/dd/yy format
# interval: 1 day
# get_history(symbol, start_date, end_date, interval)
hist = binance.get_history("XRPBTC", "01/01/18", "04/01/18", "1d")

# let's save this in a file called XRPBTC_daily.csv
binance.save_historical_data(hist, "XRPBTC_daily.csv")

# sample file saved in repository
```
