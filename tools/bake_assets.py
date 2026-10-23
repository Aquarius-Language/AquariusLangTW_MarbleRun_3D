#!/usr/bin/env python3
"""Bake the photoreal environment and material assets used by the marble run.

Inputs are CC0 assets from Poly Haven (downloaded into tools/.cache when missing):
  * HDRI  kloofendal_48d_partly_cloudy_puresky (4k .hdr)  - Greg Zaal / Poly Haven, CC0
  * Texture concrete_floor_02 (1k diff / nor_gl / arm)     - Poly Haven, CC0
  * Texture aerial_grass_rock (1k diff / nor_gl / arm)     - Poly Haven, CC0

Outputs (all gzip, the exact layout expected by Processing.loadTexture):
  assets/env_specular.gz   cube rgba16float 128px, 8 GGX-prefiltered mips (sun removed)
  assets/sky.gz            upper-hemisphere octahedral map 768px, rgba8unorm RGBM (sun removed)
  assets/<name>_albedo.gz  2D rgba8unorm-srgb (concrete 512px, grass 256px), full mips: RGB albedo, A roughness
  assets/<name>_normal.gz  2D rgba8unorm, same size, full mips: RG normal (OpenGL +Y), B ambient occlusion
  environment.aqua         generated constants: sun direction/irradiance, SH9 irradiance, sky scale

Requires Python 3.9+, NumPy and Pillow.  Run from the repository root:
  python tools/bake_assets.py
"""
import argparse
import gzip
import math
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdr_io import read_hdr  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'tools', '.cache')
HDRI = 'kloofendal_48d_partly_cloudy_puresky'
TEXTURES = {'concrete': ('concrete_floor_02', 512), 'grass': ('aerial_grass_rock', 256)}
PH = 'https://dl.polyhaven.org/file/ph-assets'

# Desired world-space horizontal direction toward the sun (x, z).  The course runs
# towards -Z, so a front-left sun throws readable shadows towards the follow camera.
SUN_HORIZONTAL = (-0.5, -0.866)
GROUND_ALBEDO = 0.24
SPEC_SIZE, SPEC_MIPS = 128, 8
SKY_SIZE, SKY_RANGE = 768, 8.0


def fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print('download', url)
        urllib.request.urlretrieve(url, path)
    return path


def write_gz(path, data):
    with open(path, 'wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=9, mtime=0, filename='') as f:
            f.write(data)
    print('wrote', os.path.relpath(path, ROOT), os.path.getsize(path), 'bytes (raw', len(data), ')')


# ---------------------------------------------------------------- directions
def equirect_dir(u, v):
    """u,v in [0,1] -> unit direction, u=0.5 faces -Z, +Y is up."""
    phi = (u - 0.5) * 2 * np.pi
    theta = v * np.pi
    st = np.sin(theta)
    return np.stack([st * np.sin(phi), np.cos(theta), -st * np.cos(phi)], -1)


def dir_equirect(d):
    u = np.arctan2(d[..., 0], -d[..., 2]) / (2 * np.pi) + 0.5
    v = np.arccos(np.clip(d[..., 1], -1, 1)) / np.pi
    return u, v


def cube_dirs(size):
    c = (np.arange(size) + 0.5) / size * 2 - 1
    t, s = np.meshgrid(c, c, indexing='ij')  # t: rows (down), s: columns
    one = np.ones_like(s)
    faces = [np.stack([one, -t, -s], -1), np.stack([-one, -t, s], -1),
             np.stack([s, one, t], -1), np.stack([s, -one, -t], -1),
             np.stack([s, -t, one], -1), np.stack([-s, -t, -one], -1)]
    d = np.stack(faces)
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def hemi_oct_dirs(size, sub=2):
    """Upper-hemisphere octahedral map with sub x sub supersampling offsets."""
    out = []
    for oy in range(sub):
        for ox in range(sub):
            y = (np.arange(size) + (oy + 0.5) / sub) / size * 2 - 1
            x = (np.arange(size) + (ox + 0.5) / sub) / size * 2 - 1
            qy, qx = np.meshgrid(y, x, indexing='ij')
            px, pz = (qx + qy) * 0.5, (qx - qy) * 0.5
            py = 1 - np.abs(px) - np.abs(pz)
            d = np.stack([px, py, pz], -1)
            out.append(d / np.linalg.norm(d, axis=-1, keepdims=True))
    return out


# ---------------------------------------------------------------- sampling
class Pyramid:
    def __init__(self, img):
        self.levels = [img.astype(np.float32)]
        while self.levels[-1].shape[0] > 4:
            a = self.levels[-1]
            self.levels.append(0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]))

    def bilinear(self, level, u, v):
        img = self.levels[level]
        h, w, _ = img.shape
        x = u * w - 0.5
        y = np.clip(v * h - 0.5, 0, h - 1)
        x0 = np.floor(x).astype(np.int64)
        y0 = np.floor(y).astype(np.int64)
        fx = (x - x0)[..., None]
        fy = (y - y0)[..., None]
        x0 %= w
        x1 = (x0 + 1) % w
        y1 = np.minimum(y0 + 1, h - 1)
        return ((img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) +
                (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy)

    def sample(self, d, lod):
        u, v = dir_equirect(d)
        lod = np.clip(lod, 0, len(self.levels) - 1)
        l0 = np.floor(lod).astype(np.int64)
        f = (lod - l0)[..., None]
        out = np.zeros(d.shape[:-1] + (3,), np.float32)
        for level in np.unique(l0):
            m = l0 == level
            a = self.bilinear(level, u[m], v[m])
            b = self.bilinear(min(level + 1, len(self.levels) - 1), u[m], v[m])
            out[m] = a * (1 - f[m]) + b * f[m]
        return out


def rotate_y(d, angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.stack([c * d[..., 0] + s * d[..., 2], d[..., 1], -s * d[..., 0] + c * d[..., 2]], -1)


# ---------------------------------------------------------------- environment
def bake_environment(out_assets):
    path = fetch(f'{PH}/HDRIs/hdr/4k/{HDRI}_4k.hdr', HDRI + '_4k.hdr')
    env = read_hdr(path)
    h, w, _ = env.shape
    lum = env @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    theta = (np.arange(h) + 0.5) / h * np.pi
    d_omega = (np.pi / h) * (2 * np.pi / w) * np.sin(theta)

    # Remove the sun disk (energy above a threshold, ~1 degree around the peak).
    py, px = np.unravel_index(np.argmax(lum), lum.shape)
    r = int(round(w / 360 * 1.2))
    ys, xs = slice(py - r, py + r + 1), slice(px - r, px + r + 1)
    clamp_level = 100.0
    window = env[ys, xs]
    wl = lum[ys, xs]
    excess = np.maximum(wl - clamp_level, 0) / np.maximum(wl, 1e-6)
    removed = window * excess[..., None]
    sun_e = (removed * d_omega[ys, None, None]).sum((0, 1))
    weights = (removed.sum(-1) * d_omega[ys, None])
    vv, uu = np.meshgrid((np.arange(py - r, py + r + 1) + 0.5) / h, (np.arange(px - r, px + r + 1) + 0.5) / w, indexing='ij')
    sun_img = (equirect_dir(uu, vv) * weights[..., None]).sum((0, 1))
    sun_img /= np.linalg.norm(sun_img)
    env[ys, xs] = window - removed

    # Yaw so the sun sits at SUN_HORIZONTAL in world space.  lookup = rotate_y(world, yaw)
    phi_img = math.atan2(sun_img[0], -sun_img[2])
    phi_world = math.atan2(SUN_HORIZONTAL[0], -SUN_HORIZONTAL[1])
    yaw = phi_world - phi_img
    sun_world = rotate_y(sun_img[None], -yaw)[0]
    print('sun dir world', sun_world, 'elevation', math.degrees(math.asin(sun_world[1])), 'E', sun_e)

    # Horizontal sky irradiance (sun removed) for the ground fill.
    up = (theta < np.pi / 2)[:, None, None]
    e_sky_h = (env * (np.cos(theta) * d_omega)[:, None, None] * up).sum((0, 1))
    e_sun_h = sun_e * max(sun_world[1], 0)
    ground = GROUND_ALBEDO / np.pi * (e_sky_h + 0.9 * e_sun_h)
    print('E sky horizontal', e_sky_h, 'ground radiance', ground)

    # Lower hemisphere -> ground with a hazy horizon blend (6 degrees).
    horizon_row = int(h / 2)
    horizon = env[horizon_row - 8:horizon_row].mean((0, 1))
    elev = 90 - np.degrees(theta)
    t = np.clip(-elev / 6.0, 0, 1)[:, None, None]
    below = (elev < 0)[:, None, None]
    fill = horizon * (1 - t) + ground * t
    env = np.where(below, fill, env).astype(np.float32)

    pyr4k = Pyramid(env)
    half = pyr4k.levels[1]  # 2048 x 1024 base for filtering
    pyr = Pyramid(half)

    # ---- specular cube (rgba16float), mip k roughness k/(N-1)
    data = []
    base_omega = 4 * np.pi / (half.shape[0] * half.shape[1])
    for mip in range(SPEC_MIPS):
        size = max(1, SPEC_SIZE >> mip)
        n = cube_dirs(size).reshape(-1, 3)
        world = n
        look = rotate_y(world, yaw)
        rough = mip / (SPEC_MIPS - 1)
        if mip == 0:
            texel = 4 * np.pi / (6 * size * size)
            lod = np.full(len(look), 0.5 * math.log2(texel / base_omega))
            col = pyr.sample(look, lod)
        else:
            col = prefilter_ggx(pyr, look, rough, base_omega, 256 if size > 8 else 512)
        rgba = np.concatenate([col, np.ones((len(col), 1), np.float32)], -1)
        data.append(np.clip(rgba, 0, 60000).astype('<f2').tobytes())
        print(' spec mip', mip, size, 'rough %.3f' % rough)
    write_gz(os.path.join(out_assets, 'env_specular.gz'), b''.join(data))

    # ---- SH9 irradiance (Lambert-convolved, divided by pi)
    small = pyr.levels[2]  # 512 x 256
    sh_h, sh_w, _ = small.shape
    vv, uu = np.meshgrid((np.arange(sh_h) + 0.5) / sh_h, (np.arange(sh_w) + 0.5) / sh_w, indexing='ij')
    look_dirs = equirect_dir(uu, vv)
    world_dirs = rotate_y(look_dirs, -yaw)
    th = (np.arange(sh_h) + 0.5) / sh_h * np.pi
    dw = ((np.pi / sh_h) * (2 * np.pi / sh_w) * np.sin(th))[:, None]
    x, y, z = world_dirs[..., 0], world_dirs[..., 1], world_dirs[..., 2]
    basis = [0.282095 * np.ones_like(x), 0.488603 * y, 0.488603 * z, 0.488603 * x,
             1.092548 * x * y, 1.092548 * y * z, 0.315392 * (3 * z * z - 1), 1.092548 * x * z, 0.546274 * (x * x - y * y)]
    band = [np.pi, 2 * np.pi / 3, 2 * np.pi / 3, 2 * np.pi / 3] + [np.pi / 4] * 5
    sh = []
    for b, a in zip(basis, band):
        c = (small * (b * dw)[..., None]).sum((0, 1)) * a / np.pi
        sh.append(c)
    sh = np.array(sh)

    # ---- sky background: upper hemisphere octahedral RGBM (rgba8unorm)
    acc = np.zeros((SKY_SIZE, SKY_SIZE, 3), np.float32)
    texel_omega = 2 * np.pi / (SKY_SIZE * SKY_SIZE)
    base4k = 4 * np.pi / (env.shape[0] * env.shape[1])
    subs = hemi_oct_dirs(SKY_SIZE, 2)
    for d in subs:
        look = rotate_y(d.reshape(-1, 3), yaw)
        lod = np.full(len(look), max(0.0, 0.5 * math.log2(texel_omega / 4 / base4k)))
        acc += pyr4k.sample(look, lod).reshape(SKY_SIZE, SKY_SIZE, 3)
    acc /= len(subs)
    m = np.clip(acc.max(-1) / SKY_RANGE, 1e-6, 1.0)
    m = np.ceil(m * 255) / 255
    rgb = np.clip(acc / (m[..., None] * SKY_RANGE), 0, 1)
    rgbm = np.concatenate([rgb, m[..., None]], -1)
    write_gz(os.path.join(out_assets, 'sky.gz'), np.round(rgbm * 255).astype(np.uint8).tobytes())
    preview = np.clip((acc / (1 + acc)) ** (1 / 2.2), 0, 1)
    Image.fromarray((preview * 255).astype(np.uint8)).save(os.path.join(CACHE, 'sky_preview.png'))
    return {'sun': sun_world, 'sun_e': sun_e, 'sh': sh, 'ground': ground, 'horizon': horizon}


def hammersley(n):
    i = np.arange(n, dtype=np.uint32)
    b = i.copy()
    b = ((b << 16) | (b >> 16)) & 0xFFFFFFFF
    b = ((b & 0x55555555) << 1) | ((b & 0xAAAAAAAA) >> 1)
    b = ((b & 0x33333333) << 2) | ((b & 0xCCCCCCCC) >> 2)
    b = ((b & 0x0F0F0F0F) << 4) | ((b & 0xF0F0F0F0) >> 4)
    b = ((b & 0x00FF00FF) << 8) | ((b & 0xFF00FF00) >> 8)
    return (i + 0.5) / n, b.astype(np.float64) / 2 ** 32


def prefilter_ggx(pyr, n, rough, base_omega, count):
    """Filtered importance sampling of a GGX lobe, N=V=R (Karis 2013)."""
    a = max(rough * rough, 1e-4)
    u1, u2 = hammersley(count)
    phi = 2 * np.pi * u1
    cos_t = np.sqrt((1 - u2) / (1 + (a * a - 1) * u2))
    sin_t = np.sqrt(1 - cos_t * cos_t)
    hl = np.stack([sin_t * np.cos(phi), sin_t * np.sin(phi), cos_t], -1)  # tangent space
    up = np.where(np.abs(n[:, 2:3]) < 0.999, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
    tx = np.cross(up, n)
    tx /= np.linalg.norm(tx, axis=-1, keepdims=True)
    ty = np.cross(n, tx)
    acc = np.zeros((len(n), 3), np.float64)
    wsum = np.zeros((len(n), 1), np.float64)
    for k in range(count):
        hvec = tx * hl[k, 0] + ty * hl[k, 1] + n * hl[k, 2]
        ndh = np.sum(n * hvec, -1, keepdims=True)
        lvec = 2 * ndh * hvec - n
        ndl = np.sum(n * lvec, -1, keepdims=True)
        ok = ndl[:, 0] > 0
        if not ok.any():
            continue
        cos_h = hl[k, 2]
        dd = (cos_h * cos_h * (a * a - 1) + 1)
        d = a * a / (np.pi * dd * dd)
        pdf = d * cos_h / (4 * cos_h) + 1e-6
        omega_s = 1.0 / (count * pdf)
        lod = 0.5 * math.log2(max(omega_s / base_omega, 1.0)) + 1.0
        col = pyr.sample(lvec[ok], np.full(ok.sum(), lod))
        acc[ok] += col * ndl[ok]
        wsum[ok] += ndl[ok]
    return (acc / np.maximum(wsum, 1e-6)).astype(np.float32)


# ---------------------------------------------------------------- materials
def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def load_rgb(path, size):
    im = Image.open(path).convert('RGB').resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255


def down2(a):
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def bake_material(key, asset, size, out_assets):
    diff = fetch(f'{PH}/Textures/png/1k/{asset}/{asset}_diff_1k.png', f'{asset}_diff_1k.png')
    nor = fetch(f'{PH}/Textures/png/1k/{asset}/{asset}_nor_gl_1k.png', f'{asset}_nor_gl_1k.png')
    arm = fetch(f'{PH}/Textures/png/1k/{asset}/{asset}_arm_1k.png', f'{asset}_arm_1k.png')
    albedo = srgb_to_linear(load_rgb(diff, size))
    n = load_rgb(nor, size) * 2 - 1
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    a = load_rgb(arm, size)
    ao, alpha2 = a[..., 0], np.clip(a[..., 1], 0.04, 1) ** 4  # store GGX alpha^2 for filtering
    albedo_mips, normal_mips = [], []
    cur_alb, cur_n, cur_ao, cur_a2 = albedo, n, ao, alpha2
    while True:
        length = np.linalg.norm(cur_n, axis=-1)
        nn = cur_n / np.maximum(length[..., None], 1e-6)
        # Toksvig-style widening: shortened averaged normals mean extra microfacet variance.
        variance = np.clip((1 - length) / np.maximum(length, 1e-3), 0, 1)
        rough = np.clip((cur_a2 + 2 * variance) ** 0.25, 0.04, 1)
        alb8 = np.concatenate([linear_to_srgb(cur_alb), rough[..., None]], -1)
        nrm8 = np.concatenate([nn[..., :2] * 0.5 + 0.5, cur_ao[..., None], np.ones_like(cur_ao)[..., None]], -1)
        albedo_mips.append(np.round(np.clip(alb8, 0, 1) * 255).astype(np.uint8).tobytes())
        normal_mips.append(np.round(np.clip(nrm8, 0, 1) * 255).astype(np.uint8).tobytes())
        if cur_alb.shape[0] == 1:
            break
        cur_alb, cur_n, cur_ao, cur_a2 = down2(cur_alb), down2(cur_n), down2(cur_ao), down2(cur_a2)
    print(key, 'mips', len(albedo_mips), 'mean albedo', albedo.mean((0, 1)))
    write_gz(os.path.join(out_assets, f'{key}_albedo.gz'), b''.join(albedo_mips))
    write_gz(os.path.join(out_assets, f'{key}_normal.gz'), b''.join(normal_mips))
    return size, len(albedo_mips)


def fmt(v):
    text = ('%.8f' % float(v)).rstrip('0')
    if text.endswith('.'):
        text += '0'
    return text + 'd'


def write_environment(env, textures):
    sun, e = env['sun'], env['sun_e']
    lines = [
        '# 由 tools/bake_assets.py 自動產生；請勿手動修改。',
        '# HDRI：Poly Haven「kloofendal_48d_partly_cloudy_puresky」（CC0），太陽已自環境貼圖移出並改以解析光源計算。',
        f'變數 太陽方向 = [{fmt(sun[0])}, {fmt(sun[1])}, {fmt(sun[2])}];',
        f'變數 太陽照度 = [{fmt(e[0])}, {fmt(e[1])}, {fmt(e[2])}];',
        f'變數 天空編碼範圍 = {fmt(SKY_RANGE)};',
        f'變數 天空貼圖尺寸 = {SKY_SIZE};',
        f'變數 反射貼圖尺寸 = {SPEC_SIZE};',
        f'變數 反射貼圖層數 = {SPEC_MIPS};',
        '變數 材質貼圖 = {' + ', '.join(f'"{k}": [{v[0]}, {v[1]}]' for k, v in textures.items()) + '};',
        f'變數 地面輻射 = [{fmt(env["ground"][0])}, {fmt(env["ground"][1])}, {fmt(env["ground"][2])}];',
        f'變數 地平線色彩 = [{fmt(env["horizon"][0])}, {fmt(env["horizon"][1])}, {fmt(env["horizon"][2])}];',
        '# 九項球諧輻照度係數（已含 Lambert 卷積並除以 π），依序為 L00、L1-1、L10、L11、L2-2、L2-1、L20、L21、L22。',
        '變數 球諧係數 = [',
    ]
    for i, c in enumerate(env['sh']):
        lines.append(f'    [{fmt(c[0])}, {fmt(c[1])}, {fmt(c[2])}]' + (',' if i < 8 else ''))
    lines.append('];')
    with open(os.path.join(ROOT, 'environment.aqua'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote environment.aqua')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--skip-environment', action='store_true')
    args = parser.parse_args()
    out = os.path.join(ROOT, 'assets')
    os.makedirs(out, exist_ok=True)
    textures = {}
    for key, (asset, size) in TEXTURES.items():
        textures[key] = bake_material(key, asset, size, out)
    if not args.skip_environment:
        write_environment(bake_environment(out), textures)


if __name__ == '__main__':
    main()
