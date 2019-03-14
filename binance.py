import requests
import json
import time
import os
import hmac
import hashlib
import logging
from urllib.parse import urlencode
from operator import itemgetter

class BinancePublic():
    def __init__(self):
        self.url = "https://api.binance.com"

        LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig(filename = "public_client.log",
                            level = logging.DEBUG,
                            format = LOG_FORMAT,
                            filemode = "w")
        self.log = logging.getLogger()

        self.log.info("PublicClient INITIALIZED")

    def check_response(self, r):
        if r.status_code != 200:
            self.log.error("")
            self.log.error("REQUEST FAIL - ERROR CODE {} - {}".format(r.json()["code"], r.json()["msg"]))
            # raise Exception("ERROR: API request unsuccessful")

    def ping(self):
        # check server time
        # parameters: none
        # weight: 1
        r = requests.get(self.url + "/api/v1/ping")
        self.log.info("PING")
        self.check_response(r)
        return r.json()

    def get_server_time(self):
        # check server time
        # parameters: none
        # weight: 1
        r = requests.get(self.url + "/api/v1/time")
        self.log.info("GET SERVER TIME")
        self.check_response(r)
        return r.json()

    def get_exchange_info(self):
        # trading rules and symbol info
        # parameters: none
        # weight: 1
        r = requests.get(self.url + "/api/v1/exchangeInfo")
        self.log.info("GET EXCHANGE INFO")
        self.check_response(r)
        return r.json()

    def get_symbols(self):
        r = self.get_exchange_info()
        symbols = []
        for symbol in r["symbols"]:
            symbols.append(symbol["symbol"])
        self.log.info("GET SYMBOLS")
        return sorted(symbols)

    def get_orderbook(self, symbol, limit=50):
        # get orderbook
        # parameters: symbol, limit
        # weight: depends on limit. weight = 1 up to limit = 100
        params = {
            "symbol": symbol,
            "limit": limit,
        }
        r = requests.get(self.url + "/api/v1/depth", params)
        self.log.info("GET ORDERBOOK")
        self.check_response(r)
        return r.json()

    def get_bids(self, symbol, limit=50):
        r = self.get_orderbook(symbol, limit)
        bids = []
        for bid in r["bids"]:
            bids.append([bid[0], bid[1]])
        self.log.info("GET BIDS")
        return bids

    def get_asks(self, symbol, limit=50):
        r = self.get_orderbook(symbol, limit)
        asks = []
        for ask in r["asks"]:
            asks.append([ask[0], ask[1]])
        self.log.info("GET ASKS")
        return asks

    def get_history(self, symbol, start_day=None, end_day=None, interval="1d", limit=500):
        # get historical price data
        #
        # symbol (string)
        #
        #
        # start_day/end_day must be in mm/dd/yy (string) format
        #
        # limit: max 500
        #
        # possible interval values (default 1d):
        # 1, 3, 5, 15, 30m
        # 1, 2, 4, 6, 8, 12h
        # 1, 3d
        # 1w
        # 1M
        #
        #
        # returns:
        # [
        #     [
        #         0   open time,
        #         1   open,
        #         2   high,
        #         3   low,
        #         4   close,
        #         5   volume,
        #         6   close time
        #         7   quote asset volume,
        #         8   number of trades,
        #         9   taker buy base asset volume,
        #         10  taker buy quote asset volume,
        #         11  ignore
        #     ]
        # ]

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }

        if start_day is None and end_day is None:
            # default: 30 days back
            startTime = int(time.time() - 3600*24*30)
            endTime = int(time.time())

        if start_day is None and end_day is not None:
            # if only end_day is specified, go back 30 days from that
            endTime = int(time.mktime(time.strptime(end_day, "%m/%d/%y")))
            startTime = endTime - 3600*24*30

        if start_day is not None and end_day is None:
            # if only start day is speficied, go forward 30 days after that
            startTime = int(time.mktime(time.strptime(start_day, "%m/%d/%y")))
            endTime = startTime + 3600*24*30

        if start_day is not None and end_day is not None:
            # if both start_day and end_day are specified
            startTime = int(time.mktime(time.strptime(start_day, "%m/%d/%y")))
            endTime = int(time.mktime(time.strptime(end_day, "%m/%d/%y")))

        if interval == ("5m" or "15m" or "30m"):
            divisor = 1000*60*5
        elif interval == ("1h" or "2h" or "4h" or "6h" or "8h" or "12h"):
            divisor = 1000*3600*1
        elif interval == ("1d" or "3d"):
            divisor = 1000*3600*24
        elif interval == ("1w" or "1M"):
            divisor = 1000*3600*24*7
        else:
            divisor = 1000*60*1

        divisor = divisor * 500

        startTime = startTime*1000
        endTime = endTime*1000

        # need to add +1 for edge case when int floors to 0
        intervals = int((endTime - startTime) / divisor + 1)

        diff = int((endTime - startTime) / intervals)

        runningTime = startTime + diff

        response = []

        breakout = False

        self.log.info("GET HISTORY - starting")

        while(runningTime <= endTime):
            params["startTime"] = startTime
            params["endTime"] = runningTime


            # let's not troll the API
            time.sleep(1)
            r = requests.get(self.url + "/api/v1/klines", params)
            self.check_response(r)
            r = r.json()
            for data in r:
                response.append(data)
            startTime += diff
            runningTime += diff


            if breakout:
                break

            if runningTime > endTime:
                runningTime = endTime
                breakout = True

        self.log.info("GET HISTORY - finished")
        # print("Data gathered.")
        return response

    def print_history(self, history):
        for row in history:
            print(f"{row[0]} \t {row[6]} \t {row[4]}")

    def save_historical_data(self, data, filename):
        # save historical data in .csv file
        # open time, close time, open, high, low, close, volume
        f = open(filename, "w")
        for row in data:
            # open_time = str(time.ctime(row[0]/1000))
            # close_time = str(time.ctime(row[6]/1000))
            open_time = str(int(row[0]/1000))
            close_time = str(int(row[6]/1000))
            open_price = row[1]
            high = row[2]
            low = row[3]
            close = row[4]
            volume = row[5]
            f.write(open_time)
            f.write(",")
            f.write(close_time)
            f.write(",")
            f.write(open_price)
            f.write(",")
            f.write(high)
            f.write(",")
            f.write(low)
            f.write(",")
            f.write(close)
            f.write(",")
            f.write(volume)
            f.write("\n")
        f.close()
        # print("Data saved.")
        self.log.info("SAVED HISTORICAL DATA IN {}".format(filename))

    def get_latest_price(self, symbol=None):
        # symbol price ticker
        # parameters: symbol (not mandatory)
        # weight: 1
        if symbol is None:
            r = requests.get(self.url + "/api/v3/ticker/price")
        else:
            params = {"symbol": symbol}
            r = requests.get(self.url + "/api/v3/ticker/price", params)
        self.log.info("GET LATEST PRICE")
        self.check_response(r)
        return r.json()

    def get_best_price(self, symbol=None):
        # symbol order book ticker
        # best price/qty on the order book for symbol
        # parameters: symbol (not mandatory)
        # weight: 1

        if symbol is None:
            r = requests.get(self.url + "/api/v3/ticker/bookTicker")
        else:
            params = {"symbol": symbol}
            r = requests.get(self.url + "/api/v3/ticker/bookTicker", params)

        self.log.info("GET BEST PRICE")
        self.check_response(r)
        return r.json()

    def get_24hr_stats(self, symbol=None):
        # 24hr ticker price change statistics
        # 24hr price change statistics
        # parameters: symbol (not mandatory)
        # weight: 1 for a single symbol
        # OR
        # weight: (number of trading symbols / 2) when symbol param is omitted

        if symbol is None:
            r = requests.get(self.url + "/api/v3/ticker/24hr")
        else:
            params = {"symbol": symbol}
            r = requests.get(self.url + "/api/v3/ticker/24hr", params)

        self.log.info("GET 24HR STATS")

        return r.json()

class BinancePrivate(BinancePublic):

    def __init__(self):
        self.url = "https://api.binance.com"
        # self.public_key = os.getenv("BINANCE_API")
        # self.private_key = os.getenv("BINANCE_API_SECRET")

        self.public_key = 0
        self.private_key = 0

        LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig(filename = "private_client.log",
                            level = logging.DEBUG,
                            format = LOG_FORMAT,
                            filemode = "w")
        self.log = logging.getLogger()

        self.log.info("PrivateClient INITIALIZED")

    def private_query(self, method, endpoint, params=None):

        if params is None:
            params = {}

        query = urlencode(sorted(params.items()))
        query += "&timestamp={}".format(int(time.time() * 1000))
        secret = bytes(self.private_key.encode("utf-8"))

        signature = hmac.new(secret, query.encode("utf-8"), hashlib.sha256).hexdigest()

        query += "&signature={}".format(signature)

        headers = {"X-MBX-APIKEY": self.public_key}

        r = requests.request(method, self.url + endpoint + "?" + query, headers=headers)


        self.check_response(r)
        self.log.info("PRIVATE QUERY - {} {}".format(method, endpoint))
        return r.json()

    def get_account_information(self):
        # account information (user_data)
        # get current account information
        # parameters: recvWindow (long), timestamp (long, required)
        # weight: 5

        return self.private_query("GET", "/api/v3/account")

    def get_balances(self, dict_format=False):
        # weight: 5
        balances = self.get_account_information()["balances"]
        balance_list = []
        for balance in balances:
            balance_list.append([balance["asset"], balance["free"]])

        if dict_format:
            return dict(sorted(balance_list, key=itemgetter(1), reverse=True))
        return sorted(balance_list, key=itemgetter(1), reverse=True)

    def get_all_orders(self, symbol):
        # all orders (user_data)
        # get all account orders, active, canceled, or filled
        # parameters: symbol (str, req), orderId (long), limit (int), recvWindow (long)
        # weight: 5 with symbol

        params = {
            "symbol": symbol,
        }
        return self.private_query("GET", "/api/v3/allOrders", params=params)

    def get_open_orders(self):
        # all active orders (user_data)
        # weight: 1 for a single symbol
        #         40 when symbol is omitted

        return self.private_query("GET", "/api/v3/openOrders")

    def market_order(self, symbol, side, quantity, Test=False):
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity
        }
        if Test:
            endpoint = "/api/v3/order/test"
        else:
            endpoint = "/api/v3/order"

        self.log.info("MARKET ORDER - {} {} {}".format(side, quantity, symbol))
        return self.private_query("POST", endpoint, params=params)

    def limit_order(self, symbol, side, quantity, price, timeInForce="IOC", Test=False):
        # limit order
        # parameters:
        # timeInForce: GTC, IOC, FOK
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": timeInForce
        }
        if Test:
            endpoint = "/api/v3/order/test"
        else:
            endpoint = "/api/v3/order"

        self.log.info("LIMIT ORDER - {} {} {} AT {}".format(side, quantity, symbol, price))
        return self.private_query("POST", endpoint, params=params)

    def limit_buy(self, symbol, quantity, price, timeInForce="IOC", Test=False):
        return self.limit_order(symbol, "BUY", quantity, price, timeInForce, Test)

    def limit_sell(self, symbol, quantity, price, timeInForce="IOC", Test=False):
        return self.limit_order(symbol, "SELL", quantity, price, timeInForce, Test)

    # def stop_loss_order(self, symbol, side, quantity, stopPrice, Test=False):
    #     params = {
    #         "symbol": symbol,
    #         "side": side,
    #         "type": "STOP_LOSS",
    #         "quantity": quantity,
    #         "stopPrice": stopPrice
    #     }
    #     if Test:
    #         endpoint = "/api/v3/order/test"
    #     else:
    #         endpoint = "/api/v3/order"
    #
    #     self.log.info("STOP LOSS ORDER - {} {} {} AT {}".format(side, quantity, symbol, stopPrice))
    #     return self.private_query("POST", endpoint, params=params)

    def stop_loss_limit_order(self, symbol, side, quantity, price, stopPrice, timeInForce="GTC", Test=False):
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_LOSS_LIMIT",
            "quantity": quantity,
            "price": price,
            "stopPrice": stopPrice,
            "timeInForce": timeInForce,
        }
        if Test:
            endpoint = "/api/v3/order/test"
        else:
            endpoint = "/api/v3/order"

        self.log.info("STOP LOSS LIMIT ORDER - {} {} {} AT {} AFTER {} STOP".format(side, quantity, symbol, price, stopPrice))
        return self.private_query("POST", endpoint, params=params)

    def cancel_order(self, order):
        params = {
            "symbol": order["symbol"],
            "orderId": order["orderId"]
        }
        self.log.info("CANCEL ORDER - {}".format(order["orderId"]))
        return self.private_query("DELETE", "/api/v3/order", params=params)

    def cancel_all_orders(self):
        canceled = []
        orders = self.get_open_orders()
        self.log.info("CANCEL ALL ORDERS")
        for order in orders:
            cancel = self.cancel_order(order)
            canceled.append(cancel)
        return canceled
