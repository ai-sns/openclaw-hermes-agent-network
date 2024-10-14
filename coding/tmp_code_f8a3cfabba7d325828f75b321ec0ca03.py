import matplotlib.pyplot as plt
import numpy as np
import warnings

# 禁用警告
warnings.filterwarnings("ignore")

# 创建猫的身体
body = plt.Circle((0.5, 0.4), 0.3, color='gray', ec='black')

# 创建猫的头部
head = plt.Circle((0.5, 0.75), 0.2, color='gray', ec='black')

# 创建猫的眼睛
left_eye = plt.Circle((0.45, 0.8), 0.05, color='white')
right_eye = plt.Circle((0.55, 0.8), 0.05, color='white')
left_pupil = plt.Circle((0.45, 0.8), 0.02, color='black')
right_pupil = plt.Circle((0.55, 0.8), 0.02, color='black')

# 创建猫的耳朵
left_ear = plt.Polygon([[0.4, 0.9], [0.45, 1.1], [0.5, 0.9]], color='gray', ec='black')
right_ear = plt.Polygon([[0.6, 0.9], [0.55, 1.1], [0.5, 0.9]], color='gray', ec='black')

# 创建猫的嘴巴
mouth_x = [0.45, 0.5, 0.55]
mouth_y = [0.72, 0.68, 0.72]
plt.plot(mouth_x, mouth_y, color='black')

# 创建绘图区域
fig, ax = plt.subplots()
ax.add_artist(body)
ax.add_artist(head)
ax.add_artist(left_eye)
ax.add_artist(right_eye)
ax.add_artist(left_pupil)
ax.add_artist(right_pupil)
ax.add_artist(left_ear)
ax.add_artist(right_ear)

# 设置坐标轴范围
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.2)
ax.set_aspect('equal')
ax.axis('off')  # 不显示坐标轴

# 显示图形
plt.show()