# filename: draw_doraemon.py
import matplotlib.pyplot as plt
import numpy as np

# 创建一个画布
fig, ax = plt.subplots()

# 画出哆啦A梦的脸部
face = plt.Circle((0.5, 0.5), 0.4, color='deepskyblue', ec='black')
ax.add_artist(face)

# 画出哆啦A梦的眼睛
eye1 = plt.Circle((0.35, 0.65), 0.07, color='white', ec='black')
eye2 = plt.Circle((0.65, 0.65), 0.07, color='white', ec='black')
ax.add_artist(eye1)
ax.add_artist(eye2)

# 画出眼珠
pupil1 = plt.Circle((0.35, 0.65), 0.03, color='black')
pupil2 = plt.Circle((0.65, 0.65), 0.03, color='black')
ax.add_artist(pupil1)
ax.add_artist(pupil2)

# 画出嘴巴
mouth_x = np.linspace(0.35, 0.65, 100)
mouth_y = 0.4 - 0.1 * np.sqrt(0.6 - (mouth_x - 0.5)**2)
ax.plot(mouth_x, mouth_y, color='black', lw=2)

# 画出胡须
ax.plot([0.2, 0.4], [0.5, 0.5], color='black', lw=2)  # 左胡须
ax.plot([0.6, 0.8], [0.5, 0.5], color='black', lw=2)  # 右胡须

# 画出铃铛
bell = plt.Circle((0.5, 0.35), 0.05, color='yellow', ec='black')
ax.add_artist(bell)

# 设置画布
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
ax.axis('off')

# 显示图形
plt.show()