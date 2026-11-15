"""Prepara las capas del logotipo Draky en coordenadas de fotograma (1920x1080).

Genera layers.npz con:
  dragon_rgb / dragon_a   -> dragón en color original (premultiplicado)
  text_a                  -> texto "Draky / Software" (se pinta en blanco)
  acc_rgb / acc_a         -> acentos verdes (hoja de la "y" y líneas de "Software")
  dragon_metal            -> dragón en verde metalizado brillante
  text_chrome             -> texto en plateado cromado
  acc_metal               -> acentos en verde metalizado
"""
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

SRC = REPO / 'assets/logotipo/Logotipo_Color_Transparente_2048.png'
W, H = 1920, 1080
LOGO_W = 1500  # ancho del logotipo dentro del fotograma


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ramp(v, stops):
    """Mapa de color por tramos. stops: lista de (pos, (r,g,b))."""
    v = np.clip(v, stops[0][0], stops[-1][0])
    out = np.zeros(v.shape + (3,), np.float32)
    pos = np.array([s[0] for s in stops], np.float32)
    cols = np.array([s[1] for s in stops], np.float32) / 255.0
    for c in range(3):
        out[..., c] = np.interp(v, pos, cols[:, c])
    return out


def normals_from_height(h, strength):
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(h)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / n, ny / n, nz / n


def main():
    src = np.array(Image.open(SRC)).astype(np.float32) / 255.0
    a = src[..., 3]
    rgb = src[..., :3]

    # --- separar componentes en resolución original
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 20 / 255).astype(np.uint8), 8)
    big = [i for i in range(1, n) if st[i, 4] > 200]
    dragon_id = max(big, key=lambda i: st[i, 4])
    dmask = (lab == dragon_id).astype(np.uint8)
    omask = ((lab > 0) & (lab != dragon_id)).astype(np.uint8)
    # asignar píxeles de borde al componente más cercano
    dd = cv2.distanceTransform(1 - dmask, cv2.DIST_L2, 5)
    do = cv2.distanceTransform(1 - omask, cv2.DIST_L2, 5)
    is_dragon = (dd <= do).astype(np.float32)
    a_dragon = a * is_dragon
    a_other = a * (1 - is_dragon)
    # acentos (verde claro) frente a texto (verde muy oscuro)
    g = rgb[..., 1] * 255
    w_acc = smoothstep(70, 130, g)
    a_acc = a_other * w_acc
    a_text = a_other * (1 - w_acc)

    # --- encaje en el fotograma
    ys, xs = np.nonzero(a > 20 / 255)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    s = LOGO_W / (x1 - x0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    M = np.array([[s, 0, W / 2 - cx * s], [0, s, H / 2 - cy * s]], np.float32)

    def warp(img):
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    # premultiplicar antes de escalar
    dragon_pm = warp(np.dstack([rgb * a_dragon[..., None], a_dragon]))
    acc_pm = warp(np.dstack([rgb * a_acc[..., None], a_acc]))
    text_a = np.clip(warp(a_text), 0, 1)
    dragon_a = np.clip(dragon_pm[..., 3], 0, 1)
    acc_a = np.clip(acc_pm[..., 3], 0, 1)
    dragon_rgb = np.clip(dragon_pm[..., :3], 0, 1)
    acc_rgb = np.clip(acc_pm[..., :3], 0, 1)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    # ================= verde metalizado (dragón y acentos) =================
    def green_metal(rgb_pm, alpha, bevel_r):
        un = rgb_pm / np.maximum(alpha[..., None], 1e-4)
        L = (0.30 * un[..., 0] + 0.59 * un[..., 1] + 0.11 * un[..., 2])
        L = np.clip(L / 0.85, 0, 1)
        # relieve: luminancia suavizada + bisel del contorno
        dist = cv2.distanceTransform((alpha > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        bev = smoothstep(0, bevel_r, dist)
        h = 0.55 * cv2.GaussianBlur(L, (0, 0), 5) + 0.9 * cv2.GaussianBlur(bev, (0, 0), 1.5)
        nx, ny, nz = normals_from_height(h * 18, 1.0)
        ry = 2 * nz * ny  # componente vertical del reflejo
        rx = 2 * nz * nx
        # entorno con bandas (reflejo metálico)
        v = (yy - 140) / 800.0 + 0.55 * ry + 0.18 * rx + 0.25 * L
        env = 0.5 + 0.5 * np.cos(2 * np.pi * (v * 1.35 + 0.1))
        env = env ** 1.6
        # luz principal arriba-izquierda
        lx, ly, lz = -0.45, -0.55, 0.70
        ln = np.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / ln, ly / ln, lz / ln
        hx, hy, hz = lx, ly, lz + 1
        hn = np.sqrt(hx * hx + hy * hy + hz * hz)
        spec = np.clip((nx * hx + ny * hy + nz * hz) / hn, 0, 1) ** 60
        diff = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
        Lc = smoothstep(0.08, 0.95, L)
        m = np.clip(0.70 * Lc + 0.34 * env * (0.35 + 0.65 * Lc) + 0.12 * diff - 0.10, 0, 1)
        col = ramp(m, [(0.00, (0, 16, 4)), (0.20, (2, 64, 18)), (0.40, (12, 140, 36)),
                       (0.58, (55, 205, 50)), (0.76, (150, 245, 80)), (0.90, (220, 255, 165)),
                       (1.00, (250, 255, 235))])
        # conservar un poco del matiz amarillo-verdoso original
        col = 0.85 * col + 0.15 * np.clip(un * 1.15, 0, 1)
        col = np.clip(col + spec[..., None] * np.array([0.9, 1.0, 0.85]) * 0.85, 0, 1)
        # zonas blancas originales (ojo, destellos) -> blanco plateado
        w_white = smoothstep(0.50, 0.75, un.min(axis=2))
        silver = np.clip(0.80 + 0.2 * env, 0, 1)[..., None] * np.array([0.95, 0.98, 1.0])
        col = col * (1 - w_white[..., None]) + silver * w_white[..., None]
        return col * alpha[..., None]

    dragon_metal = green_metal(dragon_rgb, dragon_a, 10)
    acc_metal = green_metal(acc_rgb, acc_a, 4)

    # ================= plateado cromado (texto) =================
    tmask = (text_a > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(tmask, cv2.DIST_L2, 5)
    bev = smoothstep(0, 7, dist)
    h = cv2.GaussianBlur(bev, (0, 0), 1.2)
    nx, ny, nz = normals_from_height(h * 9, 1.0)
    ry = 2 * nz * ny
    # banda vertical de cada línea de texto (Draky / Software)
    # "Draky": de la parte alta de la D a la línea base; "Software": su propia línea
    bands = [(448, 711, 0, 748), (752, 838, 748, H)]
    vloc = np.zeros((H, W), np.float32)
    for (b0, b1, r0, r1) in bands:
        hh = max(b1 - b0, 1)
        sel = (yy >= r0) & (yy < r1)
        vloc[sel] = ((yy - b0) / hh)[sel]
    v = vloc + 0.22 * ry
    env = ramp(v, [(-0.5, (255, 255, 255)), (0.00, (248, 251, 255)), (0.28, (206, 212, 222)),
                   (0.47, (128, 134, 146)), (0.53, (44, 47, 56)), (0.60, (168, 172, 180)),
                   (0.78, (232, 234, 238)), (1.00, (150, 154, 160)), (1.5, (210, 212, 216))])
    lx, ly, lz = -0.45, -0.55, 0.70
    ln = np.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    diff = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    hx, hy, hz = lx, ly, lz + 1
    hn = np.sqrt(hx * hx + hy * hy + hz * hz)
    spec = np.clip((nx * hx + ny * hy + nz * hz) / hn, 0, 1) ** 50
    rim = 1 - nz  # bordes del bisel
    chrome = env * (0.80 + 0.25 * diff[..., None]) + spec[..., None] * 0.9 - rim[..., None] * 0.35
    chrome = np.clip(chrome, 0, 1) * text_a[..., None]

    np.savez_compressed(HERE / 'layers.npz',
                        dragon_rgb=dragon_rgb.astype(np.float32), dragon_a=dragon_a.astype(np.float32),
                        text_a=text_a.astype(np.float32), acc_rgb=acc_rgb.astype(np.float32),
                        acc_a=acc_a.astype(np.float32), dragon_metal=dragon_metal.astype(np.float32),
                        text_chrome=chrome.astype(np.float32), acc_metal=acc_metal.astype(np.float32),
                        M=M, scale=np.float32(s))

    # vistas previas
    def save(img, path):
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(path)
    base = dragon_rgb + text_a[..., None] * (1 - dragon_a[..., None])
    base = acc_rgb + base * (1 - acc_a[..., None])
    save(base, HERE / 'prev_base.png')
    metal = dragon_metal + chrome * (1 - dragon_a[..., None])
    metal = acc_metal + metal * (1 - acc_a[..., None])
    save(metal, HERE / 'prev_metal.png')
    print('escala', s, 'bandas texto', bands)


if __name__ == '__main__':
    main()
