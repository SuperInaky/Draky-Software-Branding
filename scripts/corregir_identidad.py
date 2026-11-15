#!/usr/bin/env python3
"""Corrige tres defectos de los PNG de Draky Refinado (15-11-2026).

1. Iconos (24 archivos): quita el cuadradito verde o gris suelto que hay abajo a la derecha.
2. Icono 2048 (6 archivos): el original era el de 1024 con un margen enorme alrededor, así que el
   dragón ocupaba menos de un tercio. Se rehace ampliando el de 1024 ya corregido.
3. Logotipo a color con fondo oscuro (4 archivos): el texto «Draky Software» era verde muy oscuro y
   casi no se leía sobre el fondo. Se pone en blanco, con la misma forma exacta que en la versión
   de fondo claro. Las líneas y la hoja siguen en verde.

Se ejecuta una sola vez desde la raíz del repositorio:  python3 scripts/corregir_identidad.py
Los originales siguen en incoming/Draky_Nueva_Identidad_2026.zip y en el historial de Git.
"""
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

ROOT = Path('assets')
VARIANTES = ['Color_Fondo_Claro', 'Color_Fondo_Oscuro', 'Color_Transparente',
             'Blanco_Negro_Fondo_Claro', 'Blanco_Negro_Fondo_Oscuro', 'Blanco_Negro_Transparente']


def leer(p):
    return np.array(Image.open(p).convert('RGBA')).astype(np.float32)


def guardar(arr, p, transparente):
    arr = np.clip(arr + 0.5, 0, 255).astype(np.uint8)
    if not transparente:
        arr[..., 3] = 255
    Image.fromarray(arr, 'RGBA').save(p, optimize=True)  # como los originales: RGBA


def quitar_cuadradito(img, transparente):
    n = img.shape[0]
    if transparente:
        m = (img[..., 3] > 10).astype(np.uint8)
        fondo = np.array([0, 0, 0, 0], np.float32)
    else:
        fondo = np.median(img[:8, :8].reshape(-1, 4), 0)
        m = (np.abs(img - fondo).sum(2) > 40).astype(np.uint8)
    k, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    cands = []
    for i in range(1, k):
        x, y, w, h, a = st[i]
        if 8 <= a < n * n * 0.003 and a / (w * h) > 0.75 and 1 <= w / h <= 3 and x > 0.6 * n and y > 0.6 * n:
            cands.append((x, y, w, h))
    if len(cands) != 1:
        raise SystemExit(f'esperaba 1 cuadradito y hay {len(cands)}')
    x, y, w, h = cands[0]
    g = max(2, n // 256)
    out = img.copy()
    out[max(y - g, 0):y + h + g, max(x - g, 0):x + w + g] = fondo
    return out, (x, y, w, h)


def suav(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    # 1 y 2. iconos
    for v in VARIANTES:
        transp = v.endswith('Transparente')
        for n in (256, 512, 1024):
            p = ROOT / 'icono' / f'Icono_{v}_{n}.png'
            img, caja = quitar_cuadradito(leer(p), transp)
            guardar(img, p, transp)
            print('cuadradito quitado', p.name, caja)
        # 2048 = 1024 corregido ampliado al doble (antes: 1024 con margen)
        p1024 = ROOT / 'icono' / f'Icono_{v}_1024.png'
        img = leer(p1024)
        if transp:  # ampliar con alfa premultiplicado para no crear halos
            pm = img.copy(); pm[..., :3] *= img[..., 3:4] / 255.0
            big = cv2.resize(pm, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
            a = np.clip(big[..., 3:4], 0, 255)
            big[..., :3] = np.where(a > 0, big[..., :3] * 255.0 / np.maximum(a, 1e-3), 0)
            big[..., 3:4] = a
        else:
            big = cv2.resize(img, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
        guardar(big, ROOT / 'icono' / f'Icono_{v}_2048.png', transp)
        print('rehecho', f'Icono_{v}_2048.png')

    # 3. texto blanco en el logotipo a color de fondo oscuro
    for n in (256, 512, 1024, 2048):
        po = ROOT / 'logotipo' / f'Logotipo_Color_Fondo_Oscuro_{n}.png'
        pc = ROOT / 'logotipo' / f'Logotipo_Color_Fondo_Claro_{n}.png'
        O, C = leer(po), leer(pc)
        r, g, b = C[..., 0], C[..., 1], C[..., 2]
        lum = 0.3 * r + 0.59 * g + 0.11 * b
        # dragón = componente más grande de la versión clara (se excluye)
        m = (lum < 245).astype(np.uint8)
        k, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        drag = (lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8)
        drag = cv2.dilate(drag, np.ones((3, 3), np.uint8), iterations=max(1, n // 512))
        # líneas y hoja: núcleo verde vivo, ampliado un poco para cubrir sus bordes suavizados
        nucleo = ((g - np.maximum(r, b) > 55) & (g > 110)).astype(np.uint8)
        acento = cv2.dilate(nucleo, np.ones((3, 3), np.uint8), iterations=max(1, n // 512)).astype(np.float32)
        acento = cv2.GaussianBlur(acento, (0, 0), max(0.6, n / 1024))
        cob = np.clip((255 - lum) / (255 - 30), 0, 1)        # cobertura del texto oscuro
        a = (cob * (1 - acento) * (1 - drag))[..., None]
        blanco = np.array([250, 250, 250, 255], np.float32)
        out = O * (1 - a) + blanco * a
        out[..., 3] = 255
        guardar(out, po, False)
        print('texto en blanco', po.name)


if __name__ == '__main__':
    main()
