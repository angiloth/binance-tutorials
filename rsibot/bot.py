import websocket, json, pprint, talib, numpy
import config
from binance.client import Client
from binance.enums import SIDE_SELL, SIDE_BUY, ORDER_TYPE_MARKET


class BinanceClient():
    """ The hook to binance client for making buy/sell orders """

    #staticmethod
    def order(side, quantity, symbol,order_type=ORDER_TYPE_MARKET):
        client = Client(config.API_KEY, config.API_SECRET, tld='nz')
        try:
            print("sending order")
            order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
            print(order)
        except Exception as e:
            print("an exception occured - {}".format(e))
            return False

        return True

class CryptoAsset():
    """
    Data Structure for a crypto asset.
    Will store info regarding a particular crypto currency and its progress,
    with the ability to save the state to disk for later recovery.
    """

    def __init__(self, trade_symbol="ETHUSD",simulation=False):
        self.trade_symbol = trade_symbol
        self.in_position = False # is money committed to asset?
        self.candle_data = {}
        self.simulation = simulation
        self.max_funds = 100
        self.trade_quantity = 0.05



    def save(self):
        pass

    def load(self):
        pass




class CryptoBot():
    """ 
    A crypto bot. Execute process_indicators on the provided dictonary
    of candle data. 

    When the indicators reveal a buy or sell potential, it will 
    make an order through the BinanceClient class.
    """


    def __init__(self):

        # RSI Attributes (todo: initialize in a factory class)
        self.RSI_PERIOD = 14
        self.RSI_OVERBOUGHT = 70
        self.RSI_OVERSOLD = 30

        self.assets = []

    def add_asset(self, asset):
        """ Add the provided asset to a list of currently processed assets.
        Args:
            asset (CryptoAsset): An instance of the CryptoAsset class, containing
                information about the asset.

        """
        self.assets.append(asset)
        # do any other initialization here, such as loading asset history
    def get_symbols(self):
        return list(set([asset.trade_symbol for asset in self.assets]))

    def process_data(self, candle_data):
        """ For a set of candle data, process the indicators
        and then determine a course of action: Buy, Sell, Pass.
        """
        for asset in self.assets:
            print (candle_data)
            asset.candle_data = candle_data[asset.trade_symbol]
            rsi_results = self.rsi_indicator(asset.candle_data)
            #todo: turn this into a factory of indicators

            #run other indicators here
            # based on indicators, process a binance order

            # temporary:
            result = rsi_results

            if result:
                self.place_order(asset, result)


    def place_order(self, asset, order_type):
        """Place the order through binance and save results to a  transaction spreadsheet.
        If simulation mode is active, skip binance.
        """

        # todo : export transaction results in a spreadhseet on disk

        if order_type == SIDE_SELL and asset.in_position:
            if asset.simulation:
                print ('Sold!', asset.trade_quantity, asset.trade_symbol)
                order_succeeded = True
            else:
                order_succeeded = BinanceClient.order(SIDE_SELL, asset.trade_quantity, asset.trade_symbol)

            if order_succeeded:
                asset.in_position = False

        if order_type == SIDE_BUY and not self.in_position:
            if asset.simulation:
                print ('Bought!', asset.trade_quantity, asset.trade_symbol)
                order_succeeded = True
            else:
                order_succeeded = BinanceClient.order(SIDE_BUY, asset.trade_quantity, asset.trade_symbol)

            if order_succeeded:
                asset.in_position = True


    def rsi_indicator(self, candle_data):
        """Based on an array of candle close prices, execute the RSI indicator.
        Args:
            candle_data(dict): The dictionary object containing our candle ticker data

        Returns:
            Binance Buy/Sell Enum, or None
        """
        closes = candle_data['closes']
        print(closes)
        if len(closes) > self.RSI_PERIOD:
            np_closes = numpy.array(closes)
            rsi = talib.RSI(np_closes, self.RSI_PERIOD)
            print("all rsis calculated so far")
            print(rsi)
            last_rsi = rsi[-1]
            print("the current rsi is {}".format(last_rsi))


            # move this section to process_indicators
            if last_rsi > self.RSI_OVERBOUGHT:
                return SIDE_SELL
            if last_rsi < self.RSI_OVERSOLD:
                return SIDE_BUY
        return None


class BinanceTickerListener():
    """ This class listens to the binance ticker and stores 
    candle data to a dictoinary. 

    args: 
        callback (method):  The function to send the candle 
            dictionary to.

    We can expand the dictionary with more information for new 
    indicators as needed
    """

    def __init__(self, callback=None, symbols=[], simulation=False):
        
        self.callback = callback
        self.symbols = symbols

        self.simulation = simulation
        self.candle_data = {}

        # initialize candle data dict
        for symbol in symbols:
            self.candle_data[symbol]={
                'closes':[]
                }

    def on_open(self, ws):
        print('opened connection') 

    def on_close(self, ws):
        print('closed connection')

    def on_message(self, ws, message):   
        """TODO: expand for multiple symbols"""
        json_message = json.loads(message)
        #pprint.pprint(json_message)
        self.store_closes(json_message)
        self.broadcast_candle_data()
        # store other data and trigger events as needed
        
    def broadcast_candle_data(self):
        self.callback(self.candle_data)

    def store_closes(self, json_message):
        """TODO: expand for multiple symbols"""
        for symbol in self.symbols:
            candle = json_message['k']
            is_candle_closed = candle['x']
            close = candle['c']
            if is_candle_closed:
                print("candle closed at {}".format(close))
                self.candle_data[symbol]['closes'].append(float(close))
                if self.trigger_close:
                    self.trigger_close(self.candle_data)


    def retrieve_binance_data(self):
        #todo: check api and configure for tracking multiple assets
        if self.callback:
            if len(self.symbols)>1:
                raise RuntimeError('Only a single symbol is supported at the moment')
            for symbol in self.symbols:
                ws = websocket.WebSocketApp(
                    self.get_binance_socket(symbol), 
                    on_open=self.on_open, 
                    on_close=self.on_close,
                    on_message=self.on_message
                )

            # RIGHT NOW THIS ONLY SUPPORTS ONE TICKER
            ws.run_forever()


    def retrieve_simulated_data(self):
        for symbol in self.symbols:

            # make an arbitrary array of close info
            fake_close_data = [float(i) for i in range(1,20)]
            self.candle_data[symbol]={
                'closes':fake_close_data,
                }
            self.broadcast_candle_data()

    def run(self):
        if self.simulation:
            self.retrieve_simulated_data()

        else:
            self.retrieve_binance_data()


    @staticmethod
    def get_binance_socket(symbol, rate="1m"):
        """ Temp hack to get socket"""
        if symbol=="ETHUSD":
            binance_socket = "wss://stream.binance.com:9443/ws/ethusdt@kline_{}".format(rate)

        return binance_socket



# Initialize a crypto asset
eth =  CryptoAsset(trade_symbol="ETHUSD", simulation=True)   

#Add it to our bot
bot = CryptoBot()
bot.add_asset(eth)

# get a list of all the symbols our bot cares about, for tracking
symbols = bot.get_symbols()

# run the listener for live data
# a callback will trigger our bot to evaluate  
listener = BinanceTickerListener(callback=bot.process_data, simulation=True, symbols=symbols)
listener.run()
