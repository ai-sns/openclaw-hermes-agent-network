# _*_ coding:utf-8 _*_
import time

import os

import shutil

import win32gui
from PIL import ImageGrab, Image
from PyQt5.QtCore import QThread, pyqtSignal
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip


class ScreenRecordThread(QThread):
    trigger = pyqtSignal(list, int, list)

    def __init__(self):
        super(ScreenRecordThread, self).__init__()
        self.recording = True
        self.area = None
        self.save_path = ''
        self.is_pause_for_save = True
        self.recordTime = 0
        self.image_list = []  # mp4 list
        self.image_gif_list = []  # gif list

    def run(self):
        if not os.path.exists('temp'):
            os.mkdir('temp')
        # else:
        #     shutil.rmtree('temp')
        #     os.mkdir('temp')
        self.is_pause_for_save = True
        self.recording = True
        self.recordTime = 0
        self.image_list = []

        t = time.time()
        imCursor = Image.open('operationlearning/res/cursor.png')
        self.image_gif_list = []
        while self.recording:
            curX, curY = win32gui.GetCursorPos()
            if self.area is None:
                image = ImageGrab.grab()
                image.paste(imCursor, box=(curX, curY), mask=imCursor)
            else:
                image = ImageGrab.grab(self.area)
                image.paste(imCursor, box=(curX - self.area[0], curY - self.area[1]), mask=imCursor)
            imageName = os.path.join('temp', '%s.jpg' % int(time.time() * 1e3))
            image.save(imageName)
            self.image_list.append(imageName)
            self.recordTime = time.time() - t
            # """生成gif"""
            # self.image_gif_list.append(imageio.imread(imageName))
        fps = len(self.image_list) / self.recordTime
        self.trigger.emit(self.image_list, fps, self.image_gif_list)


class SaveMp4Thread(QThread):
    trigger = pyqtSignal()

    def __init__(self, list, fps, path, gif_list):
        super(SaveMp4Thread, self).__init__()
        self.fps = fps
        self.path = path
        self.list = list
        self.gif_list = gif_list
        # self.gif_list = gif_list[::n] # gif n倍速
        # self.gif_list = gif_list[::-1] # gif n倍速倒放

    def run(self):
        clip = ImageSequenceClip(self.list, fps=self.fps)
        clip.write_videofile(self.path)  # to video
        # clip.write_gif(self.path.replace("mp4", "gif"))  # to gif

        # """生成gif"""
        # imageio.mimsave('what.gif',self.gif_list)
        self.trigger.emit()
        shutil.rmtree('temp')
