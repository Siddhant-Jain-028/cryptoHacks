class DataBank(object):
    """
    Bid-Ask Prices of Pairs Stored by timestamp
    """
    timestamps = []
    prices = {} #Array of Price Quotes keyed by timestamp 
    latestTimestamp = -1
    def pushNewData (self,timestamp,priceQuotes):
        """
        Expects array of PriceQuotes
        """
        if timestamp in self.timestamps:
            Exception
        else:
            self.timestamps.append(timestamp)
            self.prices[timestamp]=priceQuotes
            if self.latestTimestamp < timestamp :
                self.latestTimestamp = timestamp
    
    def getLatestPrices(self):
        if self.latestTimestamp == -1:
            Exception
        else:
            return self.prices[self.latestTimestamp]
    
    def getPrices(self,timestamp):
        if timestamp in self.timestamps:
            return self.prices[timestamp]
        else:
            Exception
class PriceQuote(object):
    """
    Stores point in time bid-ask spread for a currency pair
    """
    def __init__(self,pair,bid,ask):
        self.pair = pair
        self.bid = bid
        self.ask = ask

