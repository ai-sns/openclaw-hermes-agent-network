from classes import *
import pyautogui
import pyperclip
import os
import time
pyautogui.PAUSE = 0.5

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

companies = ['google', 'amazon', 'meta', 'apple']
# companies = ['google']


def click_image_position(img):
    time.sleep(1)
    image_1= pyautogui.locateOnScreen(img, grayscale=True,confidence=0.7)
    time.sleep(1)
    center = pyautogui.center(image_1)
    pyautogui.click(center)

while True:
    try:
        backup(CSV,PPTX).save()
        main(companies).run()
        # DRIVER.close()

        print("准备发文件...")
        os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
        time.sleep(2)
        click_image_position("search.png")
        name = 'Photon'
        pyperclip.copy(name)
        # 模拟按下和释放Ctr1键和V键
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)  # 避免操作过快
        click_image_position("sendfile.png")
        file_path = 'C:\\testfile\\market-5-2024.pptx'
        pyperclip.copy(file_path)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.press('enter')

        DRIVER.close()

    except:
        print(f"Already there's the file: {CSV}")
        print(f"Already there's the file: {PPTX}")
        break


