# Clip de apertura Draky

Clip a pantalla completa que se muestra al abrir cada aplicación Draky.

## Versión 1 (aprobada)

Archivo: `v1/Draky_Clip_Apertura_v1.mp4`. Formato: 1920×1080, 60 fps, H.264, 5,8 s y unos 0,5 MB.

| Tiempo | Qué ocurre |
|---|---|
| 0,0 – 1,45 s | El dragón del logo llega volando desde la lejanía, batiendo el ala. |
| 1,45 – 1,9 s | Frena, da los últimos aleteos y queda en la postura del logo. |
| 1,8 – 2,35 s | El resto del logo aparece en blanco desde negro. |
| 2,35 – 3,15 s | Un brillo recorre el logo desde arriba a la izquierda: el dragón pasa a verde metalizado y el texto a plateado cromado. Hay destellos en el cuerno y en la hoja. |
| 3,15 – 5,15 s | El logo queda quieto durante 2 s. |
| 5,15 – 5,8 s | Fundido a negro. |

Origen gráfico: `assets/logotipo/Logotipo_Color_Transparente_2048.png`. El texto se pasa a blanco porque en las versiones de fondo oscuro es verde muy oscuro.

### Volver a generarlo

Necesita Python 3 con numpy, opencv-python y pillow, y además ffmpeg.

```
cd clip-apertura/v1/fuente
python3 layers.py
python3 render.py Draky_Clip_Apertura_v1.mp4
```
