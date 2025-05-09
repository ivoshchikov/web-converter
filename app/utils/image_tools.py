# app/utils/image_tools.py
from io import BytesIO
from pathlib import Path
from typing import Tuple

from PIL import Image


def convert_image(data: bytes, target_fmt: str, quality: int = 80) -> Tuple[str, bytes]:
    """
    :param data:            исходные байты (как прочитали upload.read())
    :param target_fmt:      "jpeg" | "png" | ...
    :param quality:         1-100, только для jpeg
    :return: (extension, bytes) — расширение *без точки* и готовые байты
    """
    target_fmt = target_fmt.lower().strip()
    img = Image.open(BytesIO(data))

    out_buf = BytesIO()
    save_kwargs = {}

    if target_fmt in ("jpeg", "jpg"):
        save_fmt = "JPEG"
        save_kwargs["quality"] = max(1, min(quality, 100))
        ext = "jpeg"
    else:
        save_fmt = target_fmt.upper()
        ext = target_fmt

    img.save(out_buf, save_fmt, **save_kwargs)
    out_buf.seek(0)
    return ext, out_buf.read()
