"""Generate WinCip's archive symbol and Windows package assets."""
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).parent
scale = 4
canvas = Image.new('RGBA', (256 * scale, 256 * scale), (0, 0, 0, 0))
draw = ImageDraw.Draw(canvas)


def rounded(box, radius, color):
    draw.rounded_rectangle(tuple(int(n * scale) for n in box), radius=radius * scale, fill=color)


def polygon(points, color):
    draw.polygon([(int(x * scale), int(y * scale)) for x, y in points], fill=color)


def stroke(points, color, width):
    draw.line([(int(x * scale), int(y * scale)) for x, y in points],
              fill=color, width=round(width * scale), joint='curve')


rounded((27, 22, 229, 238), 40, '#123b70')
rounded((27, 18, 229, 226), 38, '#2563eb')
rounded((27, 18, 229, 92), 30, '#3987f5')
polygon([(102, 18), (154, 18), (143, 154), (113, 154)], '#123b70')
for y in range(31, 139, 16):
    offset = round((y - 18) * 11 / 136)
    left = 103 + offset
    right = 256 - left
    polygon([(left + 2, y), (left + 15, y + 5), (left + 2, y + 10)], '#b9edff')
    polygon([(right - 2, y), (right - 15, y + 5), (right - 2, y + 10)], '#61d3ee')
left_jaw = [(111, 151), (105, 126), (97, 91), (96, 51), (98, 29)]
stroke(left_jaw, '#8bdcf2', 2.5)
stroke([(256 - x, y) for x, y in left_jaw], '#8bdcf2', 2.5)
rounded((105, 141, 151, 191), 13, '#e9f8ff')
rounded((120, 153, 136, 176), 5, '#123b70')
polygon([(193, 151), (183, 151), (165, 165),
         (183, 179), (193, 179), (175, 165)], '#ffffff')

image = canvas.resize((256, 256), Image.Resampling.LANCZOS)
image.save(root / 'WinCip.ico', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
image.save(root / 'icon-preview.png')
canvas.resize((512, 512), Image.Resampling.LANCZOS).save(root / 'icon-ui.png')
image.resize((48, 48), Image.Resampling.LANCZOS).save(root / 'icon-small.png')
image.resize((128, 128), Image.Resampling.LANCZOS).save(root / 'icon-large.png')
assets = root / 'shell_extension' / 'Assets'
assets.mkdir(parents=True, exist_ok=True)
for filename, size in [('StoreLogo.png', 50), ('Square44x44Logo.png', 44), ('Square150x150Logo.png', 150)]:
    image.resize((size, size), Image.Resampling.LANCZOS).save(assets / filename)

installer = root / 'installer'
installer.mkdir(exist_ok=True)
header = Image.new('RGB', (150, 57), 'white')
small = image.resize((48, 48), Image.Resampling.LANCZOS)
header.paste(small, (94, 4), small)
header.save(installer / 'header.bmp')
welcome = Image.new('RGB', (164, 314), '#123b70')
large = image.resize((128, 128), Image.Resampling.LANCZOS)
welcome.paste(large, (18, 64), large)
fonts = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'Fonts'
font = ImageFont.truetype(str(fonts / 'segoeuib.ttf'), 23)
caption = ImageFont.truetype(str(fonts / 'segoeui.ttf'), 13)
pen = ImageDraw.Draw(welcome)
pen.text((27, 215), 'WinCip', font=font, fill='white')
pen.text((31, 247), 'COMPRESOR', font=caption, fill='#b9edff')
welcome.save(installer / 'welcome.bmp')
