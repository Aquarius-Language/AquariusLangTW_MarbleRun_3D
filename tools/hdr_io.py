"""Minimal Radiance RGBE (.hdr) reader using only NumPy (new-style RLE and flat scanlines)."""
import numpy as np

def read_hdr(path):
    with open(path, 'rb') as f:
        data = f.read()
    pos = 0
    def line():
        nonlocal pos
        end = data.index(b'\n', pos)
        text = data[pos:end].decode('latin-1')
        pos = end + 1
        return text
    if not line().startswith('#?'):
        raise ValueError('Not a Radiance HDR file')
    while True:
        text = line()
        if text.strip() == '':
            break
        if text.startswith('FORMAT=') and '32-bit_rle_rgbe' not in text:
            raise ValueError('Unsupported HDR format: ' + text)
    parts = line().split()
    if parts[0] != '-Y' or parts[2] != '+X':
        raise ValueError('Unsupported HDR orientation')
    height, width = int(parts[1]), int(parts[3])
    raw = np.frombuffer(data, dtype=np.uint8, offset=pos)
    out = np.empty((height, width, 4), np.uint8)
    p = 0
    for y in range(height):
        if 8 <= width < 32768 and raw[p] == 2 and raw[p + 1] == 2 and (int(raw[p + 2]) << 8 | int(raw[p + 3])) == width:
            p += 4
            for c in range(4):
                x = 0
                row = out[y, :, c]
                while x < width:
                    count = int(raw[p]); p += 1
                    if count > 128:
                        count -= 128
                        row[x:x + count] = raw[p]; p += 1
                    else:
                        row[x:x + count] = raw[p:p + count]; p += count
                    x += count
        else:
            out[y] = raw[p:p + width * 4].reshape(width, 4); p += width * 4
    e = out[:, :, 3].astype(np.int32)
    scale = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0).astype(np.float32)
    return out[:, :, :3].astype(np.float32) * scale[:, :, None]
