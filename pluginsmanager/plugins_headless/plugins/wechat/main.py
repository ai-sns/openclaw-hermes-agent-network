from classes import *

class main:
    def __init__(self, array):
        self.array = array
    def run(self):
        names = []
        values = []
        coins = []

        for company in self.array:
            name, value, coin = getDatas(company).webScraping()
            names.append(name)
            values.append(value)
            coins.append(coin)

        DRIVER.close()
        sheets(names,values,coins).importSheet()
        slide(CSV).importSlide()

companies = ['google', 'amazon', 'petrobras', 'apple']
# companies = ['google']

while True:
    try:
        backup(CSV,PPTX).save()
        main(companies).run()
        DRIVER.close()
    except:
        print(f"Already there's the file: {CSV}")
        print(f"Already there's the file: {PPTX}")
        break


