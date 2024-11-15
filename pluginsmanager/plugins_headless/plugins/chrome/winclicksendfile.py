import pyautogui
import pyperclip
import os
import time
pyautogui.PAUSE = 0.5

def click_image_position(img):
    time.sleep(1)
    image_1= pyautogui.locateOnScreen(img, grayscale=True)
    time.sleep(1)
    center = pyautogui.center(image_1)
    pyautogui.click(center)

if __name__=='__main__':
#指定文件夹路径
    folder_path = r'C:\dev\rpa\Stocks_RPA_Python\files'
    file_paths=[]
    names=[]#遍历文件夹中的所有文件
    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            # 获取文件的完整路径
            file_path = os.path.join(root, file_name)
            file_paths.append(file_path)
            name = file_name.split("的")[0]
            names.append(name)

        print("准备发文件...")
        os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
        time.sleep(2)
        for i in range(len(names)):
            click_image_position("search.png")
            name = names[i]
            pyperclip.copy(name)
            # 模拟按下和释放Ctr1键和V键
            pyautogui.hotkey('ctrl','v')
            pyautogui.press('enter')
            time.sleep(1)  # 避免操作过快
            click_image_position("sendfile.png")
            file_path = file_paths[i]
            pyperclip.copy(file_path)
            pyautogui.hotkey('ctrl','v')
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.press('enter')
        print("发送完成")



