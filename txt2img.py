"""一个工具类, 将文本转换为图片, 根据文本长度自动换行"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class TxtToImg:
    def __init__(self) -> None:
        self.LINE_CHAR_COUNT = 30 * 2
        self.CHAR_SIZE = 30
        self.TABLE_WIDTH = 4
        self.module_path = Path(__file__).parent / "nonebot_plugin_impact"
        self.font = str(self.module_path / "fonts" / "SIMYOU.TTF")

    async def line_break(self, line: str) -> str:
        ret = ""
        width = 0
        for char in line:
            if len(char.encode("utf8")) == 3:
                if self.LINE_CHAR_COUNT == width + 1:
                    width = 2
                    ret += "\n" + char
                else:
                    width += 2
                    ret += char
            elif char == "\n":
                width = 0
                ret += char
            elif char == "\t":
                space_count = self.TABLE_WIDTH - width % self.TABLE_WIDTH
                ret += " " * space_count
                width += space_count
            else:
                width += 1
                ret += char
            if width >= self.LINE_CHAR_COUNT:
                ret += "\n"
                width = 0
        return ret if ret.endswith("\n") else ret + "\n"

    async def txt_to_img(self, text: str, font_size: int = 30) -> bytes:
        text = await self.line_break(text)
        d_font = ImageFont.truetype(self.font, font_size)
        line_count = text.count("\n")
        image = Image.new(
            "L",
            (self.LINE_CHAR_COUNT * font_size // 2 + 50, font_size * line_count + 50),
            "white",
        )
        draw_table = ImageDraw.Draw(im=image)
        draw_table.text(xy=(25, 25), text=text, fill="#000000", font=d_font, spacing=4)
        new_img = image.convert("RGB")
        img_byte = BytesIO()
        new_img.save(img_byte, format="PNG")
        return img_byte.getvalue()


txt_to_img = TxtToImg()
