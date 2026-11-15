"""Renderiza el clip de apertura Draky (1920x1080, 60 fps) a MP4.

Uso:  python3 render.py salida.mp4            -> vídeo completo
      python3 render.py --frames 0.5,1.0,...  -> PNG sueltos para revisar
"""
import sys
from pathlib import Path
import subprocess
import numpy as np
import cv2

W, H = 1920, 1080
FPS = 60

# ---------------- tiempos (segundos) ----------------
T_FLY0 = 0.10     # aparece a lo lejos
T_ARRIVE = 1.45   # llega a su sitio
T_POSE = 1.90     # queda en la postura del logo
T_TEXT0, T_TEXT1 = 1.80, 2.35   # el texto aparece desde negro
T_SH0, T_SH1 = 2.35, 3.15       # barrido de brillo
T_FADE0, T_FADE1 = 5.15, 5.65   # 2 s quieto y fundido a negro
T_END = 5.80

HERE = Path(__file__).resolve().parent
D = np.load(HERE / 'layers.npz')
dragon_rgb, dragon_a = D['dragon_rgb'], D['dragon_a']
text_a = D['text_a']
acc_rgb, acc_a = D['acc_rgb'], D['acc_a']
dragon_metal, text_chrome, acc_metal = D['dragon_metal'], D['text_chrome'], D['acc_metal']
M = D['M']
SC = float(D['scale'])


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def src2frame(x, y):
    return M[0, 0] * x + M[0, 2], M[1, 1] * y + M[1, 2]


# ---------------- dragón: parche con margen y pirámide ----------------
ys, xs = np.nonzero(dragon_a > 0.01)
PAD = 320
bx0, by0 = xs.min() - PAD, ys.min() - PAD
bx1, by1 = xs.max() + PAD, ys.max() + PAD
pw, ph = bx1 - bx0, by1 - by0
patch = np.zeros((ph, pw, 4), np.float32)
sx0, sy0 = max(bx0, 0), max(by0, 0)
sx1, sy1 = min(bx1, W), min(by1, H)
patch[sy0 - by0:sy1 - by0, sx0 - bx0:sx1 - bx0, :3] = dragon_rgb[sy0:sy1, sx0:sx1]
patch[sy0 - by0:sy1 - by0, sx0 - bx0:sx1 - bx0, 3] = dragon_a[sy0:sy1, sx0:sx1]
pyr = [patch]
while min(pyr[-1].shape[:2]) > 16:
    pyr.append(cv2.pyrDown(pyr[-1]))

# ancla (centro del dragón) en coordenadas de fotograma
A0 = np.array([(xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0])

# ala: triángulo (coordenadas del logo original 2048) con pivote en el hombro
tri = np.array([src2frame(200, 380), src2frame(670, 678), src2frame(258, 872)], np.float32)
wing_w = np.zeros((ph, pw), np.float32)
cv2.fillPoly(wing_w, [np.round(tri - [bx0, by0]).astype(np.int32)], 1.0)
wing_w = cv2.GaussianBlur(wing_w, (0, 0), 22)
wing_w = np.clip(wing_w * 1.3, 0, 1)
_py, _px = np.mgrid[0:ph, 0:pw].astype(np.float32)
_ysrc = (_py + by0 - M[1, 2]) / M[1, 1]
wing_w *= 1 - 0.85 * smoothstep(690, 850, _ysrc)      # la cola (abajo) casi no se mueve
PIV = np.array(src2frame(600, 650)) - [bx0, by0]       # hombro
# ---------------- estado del vuelo ----------------
Z0, ZP = 16.0, 1.9
P0 = np.array([340.0, 380.0])
P1 = np.array([230.0, 640.0])
P2 = np.array([330.0, 720.0])
P3 = A0.copy()


def bezier(w):
    return ((1 - w) ** 3) * P0 + 3 * ((1 - w) ** 2) * w * P1 + 3 * (1 - w) * w * w * P2 + w ** 3 * P3


# fase del aleteo integrada (frecuencia que baja al frenar)
_tt = np.linspace(0, T_END, 4000)
_freq = np.where(_tt < T_ARRIVE, 3.1, 3.1 - 1.3 * smoothstep(T_ARRIVE, T_POSE, _tt))
_phase = np.concatenate([[0], np.cumsum(_freq[1:] * np.diff(_tt))]) * 2 * np.pi


def settle(t):
    """1 durante el vuelo; muelle amortiguado hasta 0 en la postura final."""
    if t < T_ARRIVE:
        return 1.0
    dt = t - T_ARRIVE
    v = np.exp(-5.5 * dt) * np.cos(2 * np.pi * 1.6 * dt)
    return float(v * (1 - smoothstep(T_POSE - 0.18, T_POSE, t)))


def state(t):
    u = float(np.clip((t - T_FLY0) / (T_ARRIVE - T_FLY0), 0, 1))
    z = 1 + (Z0 - 1) * (1 - u) ** ZP
    S = 1.0 / z
    w = 1 - (1 - u) ** 1.7
    pos = bezier(w)
    st = settle(t)
    phase = np.interp(t, _tt, _phase)
    flap = np.deg2rad(st * (4 + 26 * np.sin(phase)))
    bob = -np.sin(phase + 0.6) * 14 * S * st
    rot = st * (-9 + 7 * np.sin(2 * np.pi * 0.7 * t + 0.8))
    if t >= T_POSE:
        S, pos, flap, bob, rot = 1.0, A0.copy(), 0.0, 0.0, 0.0
    bright = (0.30 + 0.70 * S ** 0.45) * smoothstep(T_FLY0, T_FLY0 + 0.25, t)
    return S, pos + [0, bob], np.deg2rad(rot), flap, bright


_gy, _gx = np.mgrid[0:H, 0:W].astype(np.float32)


def render_dragon(t):
    S, pos, rot, flap, bright = state(t)
    if bright <= 0:
        return np.zeros((H, W, 3), np.float32), np.zeros((H, W), np.float32)
    # inversa de la transformación afín: fotograma -> parche
    c, s = np.cos(rot), np.sin(rot)
    dx, dy = _gx - pos[0], _gy - pos[1]
    px = (c * dx + s * dy) / S + (A0[0] - bx0)
    py = (-s * dx + c * dy) / S + (A0[1] - by0)
    # aleteo: el ala gira alrededor del hombro y se acorta en perspectiva
    if abs(flap) > 1e-4:
        pxi = np.clip(px, 0, pw - 1).astype(np.int32)
        pyi = np.clip(py, 0, ph - 1).astype(np.int32)
        inside = (px >= 0) & (px < pw) & (py >= 0) & (py < ph)
        ww = wing_w[pyi, pxi] * inside
        th = -ww * flap
        ct, stt = np.cos(th), np.sin(th)
        rx, ry = px - PIV[0], py - PIV[1]
        qx = ct * rx - stt * ry
        qy = stt * rx + ct * ry
        k = 1 - ww * 0.30 * np.abs(np.sin(flap))
        px = PIV[0] + qx / k
        py = PIV[1] + qy / k
    # nivel de la pirámide según escala
    lvl = int(np.clip(np.floor(np.log2(1.0 / max(S, 1e-3))), 0, len(pyr) - 1))
    f = 2.0 ** lvl
    img = cv2.remap(pyr[lvl], (px / f).astype(np.float32), (py / f).astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return img[..., :3] * bright, img[..., 3] * bright


# ---------------- brillo ----------------
SHEAR = 0.45
s_field = _gx + SHEAR * _gy
logo_a = np.clip(dragon_a + text_a + acc_a, 0, 1)
ys2, xs2 = np.nonzero(logo_a > 0.02)
S_MIN = float((xs2 + SHEAR * ys2).min())
S_MAX = float((xs2 + SHEAR * ys2).max())
BW = 70.0
halo_a = cv2.GaussianBlur(logo_a, (0, 0), 22)

# imagen metálica completa y su resplandor
metal_full = acc_metal + (dragon_metal + text_chrome * (1 - dragon_a[..., None])) * (1 - acc_a[..., None])
lum = metal_full.mean(axis=2)
bp = metal_full * smoothstep(0.70, 1.0, lum)[..., None]
metal_bloom = 0.22 * cv2.GaussianBlur(bp, (0, 0), 8) + 0.14 * cv2.GaussianBlur(bp, (0, 0), 26)

# destellos (estrellas)
_dy, _dx = np.nonzero(dragon_a > 0.5)
i = np.argmin(_dy)
STAR1 = (float(_dx[i]), float(_dy[i]) + 6)          # punta del cuerno
_ay, _ax = np.nonzero(acc_a > 0.5)
sel = _ay < np.percentile(_ay, 30)
j = np.argmax(_ax[sel])
STAR2 = (float(_ax[sel][j]) - 4, float(_ay[sel][j]) + 4)  # punta de la hoja


def front_at(t):
    k = smoothstep(T_SH0, T_SH1, t)
    k = float(k)
    return S_MIN - 2.2 * BW + k * (S_MAX - S_MIN + 4.4 * BW)


def time_front_reaches(x, y):
    target = x + SHEAR * y
    ts = np.linspace(T_SH0, T_SH1, 2000)
    fr = np.array([front_at(tt) for tt in ts])
    return float(ts[np.argmin(np.abs(fr - target))])


T_STAR1 = time_front_reaches(*STAR1) + 0.05
T_STAR2 = time_front_reaches(*STAR2) + 0.05


def star(img, cx, cy, t, t0, size):
    dur = 0.55
    k = (t - t0) / dur
    if k <= 0 or k >= 1:
        return
    amp = np.sin(np.pi * k) ** 1.5
    r = size * amp
    x0, x1 = int(max(cx - 3 * size, 0)), int(min(cx + 3 * size, W))
    y0, y1 = int(max(cy - 3 * size, 0)), int(min(cy + 3 * size, H))
    gx = _gx[y0:y1, x0:x1] - cx
    gy = _gy[y0:y1, x0:x1] - cy
    ang = 0.35 * k
    ca, sa = np.cos(ang), np.sin(ang)
    u = ca * gx + sa * gy
    v = -sa * gx + ca * gy
    ray = np.exp(-(u / max(r, 1)) ** 2 * 1.0 - (v / 2.2) ** 2) + np.exp(-(v / max(r, 1)) ** 2 - (u / 2.2) ** 2)
    ray2 = 0.5 * (np.exp(-((u + v) / (1.414 * max(r * 0.5, 1))) ** 2 - ((u - v) / 3.0) ** 2) +
                  np.exp(-((u - v) / (1.414 * max(r * 0.5, 1))) ** 2 - ((u + v) / 3.0) ** 2))
    core = np.exp(-(gx * gx + gy * gy) / (2 * (0.18 * size * amp + 1) ** 2))
    val = (ray * 0.9 + ray2 * 0.45 + core * 1.0) * amp
    img[y0:y1, x0:x1] += val[..., None] * np.array([1.0, 1.0, 0.95], np.float32)


# ---------------- fotograma ----------------
SUB = 5          # submuestras para desenfoque de movimiento
SHUTTER = 0.5    # fracción del fotograma


def frame(t):
    if t < T_POSE + 0.02:
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(SUB):
            tt = t + (k / (SUB - 1) - 0.5) * SHUTTER / FPS
            rgb, _ = render_dragon(tt)
            acc += rgb
        drg_rgb = acc / SUB
        drg_a = None
    else:
        drg_rgb, drg_a = dragon_rgb, dragon_a

    tf = float(smoothstep(T_TEXT0, T_TEXT1, t))
    front = front_at(t)
    shining = T_SH0 <= t <= T_SH1 + 0.05
    if t >= T_SH0:
        mt = smoothstep(front + 45, front - 45, s_field)[..., None]   # 1 = ya metálico
    else:
        mt = None

    # capa del dragón
    if mt is not None:
        drg = drg_rgb * (1 - mt) + dragon_metal * mt
    else:
        drg = drg_rgb
    # texto blanco -> cromado
    txt_white = text_a[..., None] * np.float32(0.97)
    txt = txt_white if mt is None else txt_white * (1 - mt) + text_chrome * mt
    accl = acc_rgb if mt is None else acc_rgb * (1 - mt) + acc_metal * mt
    da = dragon_a[..., None]
    img = drg + tf * (txt * (1 - da) * (1 - acc_a[..., None]) + accl)

    if mt is not None:
        img = img + metal_bloom * mt
    if shining:
        band = np.exp(-((s_field - front) / BW) ** 2)
        img = img + (band * logo_a * 0.95)[..., None] * np.array([1.0, 1.0, 0.96], np.float32)
        img = img + (band * halo_a * 0.30)[..., None] * np.array([0.85, 1.0, 0.85], np.float32)
    star(img, *STAR1, t, T_STAR1, 34)
    star(img, *STAR2, t, T_STAR2, 28)

    fade = 1 - float(smoothstep(T_FADE0, T_FADE1, t))
    img = np.clip(img * fade, 0, 1)
    return img


def to8(img, rng):
    out = img * 255 + rng.uniform(-0.5, 0.5, img.shape).astype(np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    rng = np.random.default_rng(1)
    if len(sys.argv) > 2 and sys.argv[1] == '--frames':
        for ts in sys.argv[2].split(','):
            t = float(ts)
            cv2.imwrite(str(HERE / f'f_{t:.2f}.png'), cv2.cvtColor(to8(frame(t), rng), cv2.COLOR_RGB2BGR))
        return
    out = sys.argv[1]
    n = int(round(T_END * FPS))
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p',
           '-profile:v', 'high', '-movflags', '+faststart', '-an', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(to8(frame(i / FPS), rng).tobytes())
        if i % 60 == 0:
            print('fotograma', i, '/', n, flush=True)
    p.stdin.close()
    p.wait()
    print('listo', out)


if __name__ == '__main__':
    main()
