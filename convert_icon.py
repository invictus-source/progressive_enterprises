from PIL import Image
import os

img_path = 'assets/logo.png'
ico_path = 'assets/logo.ico'

if os.path.exists(img_path):
    img = Image.open(img_path)
    size = max(img.width, img.height)
    new_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    new_img.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    new_img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print(f"Created {ico_path}")
else:
    print(f"Error: {img_path} not found")