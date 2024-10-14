# filename: floating_balloon.py
import pygame
import random

# 初始化Pygame
pygame.init()

# 设置屏幕尺寸
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))

# 设置窗口标题
pygame.display.set_caption("飘动的气球")

# 定义气球颜色
balloon_color = (255, 0, 0)  # 红色

# 定义气球初始位置
balloon_x = random.randint(0, screen_width)
balloon_y = screen_height

# 定义气球速度
balloon_speed = 2

# 设置时钟
clock = pygame.time.Clock()

# 运行时间限制（秒）
time_limit = 30
start_ticks = pygame.time.get_ticks()  # 获取开始时间

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 检查运行时间是否超过限制
    seconds = (pygame.time.get_ticks() - start_ticks) / 1000
    if seconds > time_limit:
        running = False

    # 处理气球移动
    balloon_y -= balloon_speed
    if balloon_y < 0:
        balloon_x = random.randint(0, screen_width)
        balloon_y = screen_height

    # 清屏
    screen.fill((255, 255, 255))  # 白色背景

    # 画气球
    pygame.draw.circle(screen, balloon_color, (balloon_x, balloon_y), 20)

    # 更新显示
    pygame.display.flip()

    # 控制帧率
    clock.tick(60)

pygame.quit()