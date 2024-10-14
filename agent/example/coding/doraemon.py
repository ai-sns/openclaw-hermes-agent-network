# filename: doraemon.py
import matplotlib
matplotlib.use('TkAgg')  # 指定绘图后端为TkAgg
import matplotlib.pyplot as plt
import numpy as np

# 设置图形
fig, ax = plt.subplots()

# 画脸
head = plt.Circle((0.5, 0.5), 0.4, color='deepskyblue')
ax.add_artist(head)

# 画脸部细节
face_color = 'white'
face = plt.Circle((0.5, 0.5), 0.35, color=face_color)
ax.add_artist(face)

# 画眼睛
eye1 = plt.Circle((0.35, 0.6), 0.05, color='black')
eye2 = plt.Circle((0.65, 0.6), 0.05, color='black')
ax.add_artist(eye1)
ax.add_artist(eye2)

# 画眼珠
eyeball1 = plt.Circle((0.35, 0.6), 0.02, color='white')
eyeball2 = plt.Circle((0.65, 0.6), 0.02, color='white')
ax.add_artist(eyeball1)
ax.add_artist(eyeball2)

# 画鼻子
nose = plt.Circle((0.5, 0.55), 0.03, color='red')
ax.add_artist(nose)

# 画嘴巴
mouth = np.array([[0.4, 0.45],
                  [0.5, 0.4],
                  [0.6, 0.45]])
ax.plot(mouth[:, 0], mouth[:, 1], color='black')

# 画胡须
ax.plot([0.1, 0.3], [0.5, 0.5], color='black')
ax.plot([0.1, 0.3], [0.52, 0.52], color='black')
ax.plot([0.1, 0.3], [0.48, 0.48], color='black')

# 设置图形属性
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
ax.axis('off')  # 不显示坐标轴

# 展示图形
plt.show()