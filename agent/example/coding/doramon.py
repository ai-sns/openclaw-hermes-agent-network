# filename: doramon.py
import matplotlib.pyplot as plt
import numpy as np

# 画圆形的脸部
face = plt.Circle((0.5, 0.5), 0.4, color='deepskyblue', ec='black')

# 画白色的脸部区域
white_face = plt.Circle((0.5, 0.5), 0.35, color='white', ec='black')

# 画眼睛
left_eye = plt.Circle((0.35, 0.65), 0.05, color='white', ec='black')
right_eye = plt.Circle((0.65, 0.65), 0.05, color='white', ec='black')
left_pupil = plt.Circle((0.35, 0.65), 0.02, color='black')
right_pupil = plt.Circle((0.65, 0.65), 0.02, color='black')

# 画嘴巴
x = np.linspace(0.3, 0.7, 100)
y = 0.4 - 0.1 * np.cos((x - 0.5) * np.pi)
plt.plot(x, y, color='black')

# 画胡须
plt.plot([0.1, 0.4], [0.5, 0.5], color='black')
plt.plot([0.1, 0.4], [0.48, 0.48], color='black')
plt.plot([0.1, 0.4], [0.52, 0.52], color='black')
plt.plot([0.6, 0.9], [0.5, 0.5], color='black')
plt.plot([0.6, 0.9], [0.48, 0.48], color='black')
plt.plot([0.6, 0.9], [0.52, 0.52], color='black')

# 添加到画布
fig, ax = plt.subplots()
ax.add_artist(face)
ax.add_artist(white_face)
ax.add_artist(left_eye)
ax.add_artist(right_eye)
ax.add_artist(left_pupil)
ax.add_artist(right_pupil)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
plt.axis('off')  # 隐藏坐标轴
plt.show()