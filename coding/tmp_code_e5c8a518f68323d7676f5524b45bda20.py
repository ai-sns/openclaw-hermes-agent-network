import matplotlib.pyplot as plt

# 创建一个新的图形
fig, ax = plt.subplots()

# 画猫的头
head = plt.Circle((0.5, 0.5), 0.4, color='gray')
ax.add_artist(head)

# 画猫的眼睛
left_eye = plt.Circle((0.35, 0.65), 0.05, color='white')
right_eye = plt.Circle((0.65, 0.65), 0.05, color='white')
ax.add_artist(left_eye)
ax.add_artist(right_eye)

# 画猫的瞳孔
left_pupil = plt.Circle((0.35, 0.65), 0.02, color='black')
right_pupil = plt.Circle((0.65, 0.65), 0.02, color='black')
ax.add_artist(left_pupil)
ax.add_artist(right_pupil)

# 画猫的鼻子
nose = plt.Circle((0.5, 0.55), 0.03, color='pink')
ax.add_artist(nose)

# 画猫的嘴巴
ax.plot([0.48, 0.5, 0.52], [0.5, 0.48, 0.5], color='black')

# 设置坐标轴的范围
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
ax.axis('off')  # 不显示坐标轴

# 保存图形到文件
plt.savefig('cat_image.png')  # 将图像保存为cat_image.png