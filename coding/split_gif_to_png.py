# filename: split_gif_to_png.py
from PIL import Image
import os

# 路径定义
gif_path = r'C:\Users\IDD\Pictures\character.gif'
output_folder = r'C:\Users\IDD\Pictures\character_frames'

# 确保输出目录存在
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 打开GIF文件
with Image.open(gif_path) as img:
    # 初始化帧编号
    frame_number = 0
    while True:
        # 保存当前帧为PNG文件
        frame_path = os.path.join(output_folder, f'frame_{frame_number}.png')
        img.save(frame_path, 'PNG')
        
        # 打印保存的帧路径
        print(f'Saved {frame_path}')
        
        # 尝试移动到下一帧
        try:
            img.seek(frame_number + 1)
            frame_number += 1
        except EOFError:
            # 已经到最后一帧
            break