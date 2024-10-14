from RPACommon import *

class StocksHandle:
    def __init__(self):
        self.companies = []
        self.DRIVER = getDatas('',None).DRIVER
        directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
        NOW = datetime.datetime.now()
        self.CSV = f'{directory}-{NOW.month}-{NOW.year}.csv'
        self.PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
    def run(self):
        names = []
        values = []
        coins = []

        for company in self.companies:
            name, value, coin = getDatas(company,self.DRIVER).webScraping()
            names.append(name)
            values.append(value)
            coins.append(coin)

        self.DRIVER.close()
        sheets(names,values,coins).importSheet()
        slide(self.CSV).importSlide()

    def get_Stocks(self,companies):
        # companies = ['google', 'amazon', 'meta', 'apple']
        DRIVER = self.DRIVER
        self.companies = companies

        while True:
            try:
                backup(self.CSV,self.PPTX).save()
                self.run()
                DRIVER.close()


            except:
                print(f"Already there's the file: {self.CSV}")
                print(f"Already there's the file: {self.PPTX}")
                break



