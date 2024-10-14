# filename: doramon_drawing.py
import matplotlib.pyplot as plt
import numpy as np

# 确保使用合适的后端
plt.switch_backend('TkAgg')

# 创建一个新的图形
fig, ax = plt.subplots()

# 设置图形的背景为白色
ax.set_facecolor('white')

# 画出哆啦A梦的身体
body = plt.Circle((0.5, 0.5), 0.4, color='deepskyblue')
ax.add_artist(body)

# 画出哆啦A梦的脸
face = plt.Circle((0.5, 0.5), 0.4, color='white')
ax.add_artist(face)

# 画出哆啦A梦的眼睛
left_eye = plt.Circle((0.35, 0.65), 0.07, color='white')
right_eye = plt.Circle((0.65, 0.65), 0.07, color='white')
ax.add_artist(left_eye)
ax.add_artist(right_eye)

# 画出眼睛的黑色部分
left_pupil = plt.Circle((0.35, 0.65), 0.03, color='black')
right_pupil = plt.Circle((0.65, 0.65), 0.03, color='black')
ax.add_artist(left_pupil)
ax.add_artist(right_pupil)

# 画出哆啦A梦的鼻子
nose = plt.Circle((0.5, 0.55), 0.025, color='red')
ax.add_artist(nose)

# 画出嘴巴
mouth_x = np.linspace(0.4, 0.6, 100)
mouth_y = 0.4 - 0.1 * np.sqrt(1 - ((mouth_x - 0.5) / 0.1) ** 2)
ax.plot(mouth_x, mouth_y, color='black')

# 画出胡须
ax.plot([0.25, 0.4], [0.5, 0.5], color='black')
ax.plot([0.6, 0.75], [0.5, 0.5], color='black')

# 关闭坐标轴
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

# 显示图形
plt.show()