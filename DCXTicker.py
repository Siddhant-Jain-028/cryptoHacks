import requests 
import time
import pickle
import data_bank
import threading

class DCXTicker(object):

    def pollServer(self):
        url = "https://api.coindcx.com/exchange/ticker"
        response = requests.get(url)
        data = response.json()
        print("Polling Status:",response.status_code)
        return data

    def startTicker(self,dataBank,pollInterval=1):
        self.dataBank = dataBank  
        self.isTickerActive = True  
        self.pollWorker = threading.Thread(target = self.threadedPollingWorker,args = (dataBank,pollInterval)).start()
    
    def threadedPollingWorker(self,dataBank,pollInterval):
        while self.isTickerActive:
            timestamp, prices = self.unwrapResponse(self.pollServer())
            dataBank.pushNewData ( timestamp , prices)
            print("Added Data:", time.ctime(timestamp))
            time.sleep(pollInterval)

    def stopTicker(self):
        """
        Pauses the ticker
        """
        self.isTickerActive = False

    def unwrapResponse(self,data):
        temp = []
        timestamp = data[0]['timestamp']
        for pair in data : 
            temp.append(data_bank.PriceQuote(pair['market'],pair['bid'],pair['ask']))      
        return timestamp,temp

x = DCXTicker()
db = data_bank.DataBank()
x.startTicker(db)
time.sleep(3)
x.stopTicker()
print(db.getLatestPrices()[0].bid,db.getLatestPrices()[0].pair)