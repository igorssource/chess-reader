"""Photo helpers: a smaller copy for reading the whole sheet, and a zoomed crop of one
move cell (cut from the full-resolution photo) for re-reading a doubtful move.

Pillow is optional: without it the photo is sent as it is and no crops are made.
"""
from __future__ import annotations

import io

from .model.base import Image

READ_SIDE = 1600          # the model sees about this many pixels anyway
CROP_SIDE = 1200          # longest side of a zoomed crop

try:
    from PIL import Image as _PIL, ImageOps as _Ops
except ImportError:       # pragma: no cover
    _PIL = None


def _open(data: bytes):
    im = _PIL.open(io.BytesIO(data))
    im = _Ops.exif_transpose(im)
    return im.convert("RGB")


def _jpeg(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def prepare(img: Image) -> Image:
    """Keep the uploaded photo as `hires`; `data` becomes a copy of at most READ_SIDE px."""
    if _PIL is None:
        return img
    try:
        im = _open(img.data)
    except Exception:
        return img
    if max(im.size) <= READ_SIDE:
        return Image(img.data, img.media_type, hires=img.data)
    k = READ_SIDE / max(im.size)
    small = im.resize((round(im.width * k), round(im.height * k)), _PIL.LANCZOS)
    return Image(_jpeg(small), "image/jpeg", hires=img.data)


def cell_box(layout: list[dict], number: int, color: str):
    """Rectangle (0..1000) of the cell for move `number`, column `color`, or None.
    Blocks are given by the model; rows are spread evenly inside a block."""
    for b in layout or []:
        if b["first_move"] <= number <= b["last_move"]:
            rows = b["last_move"] - b["first_move"] + 1
            rh = (b["bottom"] - b["top"]) / rows
            y = b["top"] + (number - b["first_move"]) * rh
            mid = (b["left"] + b["right"]) / 2
            x0, x1 = (b["left"], mid) if color == "w" else (mid, b["right"])
            return {"block": b, "rh": rh, "x0": x0, "x1": x1, "y0": y, "y1": y + rh}
    return None


def crop_cell(img: Image, layout: list[dict], number: int, color: str, rows_around: float = 2.5):
    """Zoomed crop around one move cell: the whole width of its block (with the printed
    move numbers) and a few rows above and below, because the layout is only approximate."""
    if _PIL is None or not layout:
        return None
    box = cell_box(layout, number, color)
    if box is None:
        return None
    try:
        im = _open(img.hires or img.data)
    except Exception:
        return None
    b = box["block"]
    bw = b["right"] - b["left"]
    x0 = max(0.0, b["left"] - 0.15 * bw)
    x1 = min(1000.0, b["right"] + 0.03 * bw)
    y0 = max(0.0, box["y0"] - rows_around * box["rh"])
    y1 = min(1000.0, box["y1"] + rows_around * box["rh"])
    W, H = im.width / 1000, im.height / 1000
    c = im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    if c.width < 20 or c.height < 20:
        return None
    k = min(CROP_SIDE / max(c.size), 3.0)
    if k != 1:
        c = c.resize((round(c.width * k), round(c.height * k)), _PIL.LANCZOS)
    return Image(_jpeg(c), "image/jpeg")
