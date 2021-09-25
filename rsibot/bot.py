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



class CryptoBot():
    """ 
    A crypto bot. Execute process_indicators on the provided dictonary
    of candle data. 

    When the indicators reveal a buy or sell potential, it will 
    make an order through the BinanceClient class.
    """


    def __init__(self, simulation=True):

        # RSI Attributes (todo: initialize in a factory class)
        self.RSI_PERIOD = 14
        self.RSI_OVERBOUGHT = 70
        self.RSI_OVERSOLD = 30
        self.TRADE_SYMBOL = 'ETHUSD'
        self.TRADE_QUANTITY = 0.05

        # in_position is a variable declaring if we already have our 
        # money committed. We should epand this logic for multiple 
        # tiered money pools
        self.in_position = False

        self.simulation=simulation


    def process_data(self, candle_data):
        """ For a set of candle data, process the indicators
        and then determine a course of action: Buy, Sell, Pass.
        """

        rsi_results = self.rsi_indicator(candle_data)
        #todo: turn this into a factory of indicators

        #run other indicators here
        # based on indicators, process a binance order

        # temporary:
        result = rsi_results

        # test
        result = SIDE_BUY
        print(self.in_position)

        if result:
            self.place_order(result)


    def place_order(self, order_type):
        """Place the order through binance and save results to a  transaction spreadsheet.
        If simulation mode is active, skip binance.
        """

        # todo : export transaction results in a spreadhseet on disk

        if order_type == SIDE_SELL and self.in_position:
            if self.simulation:
                print ('Sold!', self.TRADE_QUANTITY, self.TRADE_SYMBOL)
                order_succeeded = True
            else:
                order_succeeded = BinanceClient.order(SIDE_SELL, self.TRADE_QUANTITY, self.TRADE_SYMBOL)

            if order_succeeded:
                self.in_position = False

        if order_type == SIDE_BUY and not self.in_position:
            if self.simulation:
                print ('Bought!', self.TRADE_QUANTITY, self.TRADE_SYMBOL)
                order_succeeded = True
            else:
                order_succeeded = BinanceClient.order(SIDE_BUY, self.TRADE_QUANTITY, self.TRADE_SYMBOL)

            if order_succeeded:
                self.in_position = True


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
                if self.in_position:
                    print("Overbought! Sell! Sell! Sell!")
                    # put binance sell logic here
                    return SIDE_SELL
                else:
                    print("It is overbought, but we don't own any. Nothing to do.")
            
            if last_rsi < self.RSI_OVERSOLD:
                if in_position:

                    print("It is oversold, but you already own it, nothing to do.")
                else:
                    print("Oversold! Buy! Buy! Buy!")
                    return SIDE_BUY
        return None


class TickerListener():
    """ This class listens to the binance ticker and stores 
    candle data to a dictoinary. 

    args: 
        callback (method):  The function to send the candle 
            dictionary to.

    We can expand the dictionary with more information for new 
    indicators as needed
    """

    def __init__(self, callback=None):
        self.SOCKET = "wss://stream.binance.com:9443/ws/ethusdt@kline_1m"
        self.callback = callback

        self.candle_data = {
            'closes':[]
        }

    def on_open(self, ws):
        print('opened connection') 

    def on_close(self, ws):
        print('closed connection')

    def on_message(self, ws, message):   
        json_message = json.loads(message)
        #pprint.pprint(json_message)
        self.store_closes(json_message)
        self.callback(self.candle_data)
        # store other data and trigger events as needed
        
    def send_message(self):
        self.trigger(candle_data)

    def store_closes(self, json_message):
        candle = json_message['k']
        is_candle_closed = candle['x']
        close = candle['c']
        if is_candle_closed:
            print("candle closed at {}".format(close))
            self.candle_data['closes'].append(float(close))
            if self.trigger_close:
                self.trigger_close(self.candle_data)
                print('triggered')


    def run(self):
        ws = websocket.WebSocketApp(
            self.SOCKET, 
            on_open=self.on_open, 
            on_close=self.on_close,
            on_message=self.on_message
            )
        ws.run_forever()



bot =  CryptoBot(simulation=True)        

# run the listener for live data:     
# listener = TickerListener(callback=bot.process_data)
# listener.run()

# or feed the bot fake data:
fake_close_data = [float(i) for i in range(1,20)]
candle_data = {'closes':fake_close_data}
bot.process_data(candle_data)