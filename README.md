# Draky Software — Identidad corporativa

Repositorio oficial de recursos gráficos de Draky Software.

## Diseño aprobado

**Draky Refinado**: dragón verde integrado en la letra D, marca «Draky» y subtítulo «Software».

## Colección

- Icono cuadrado y logotipo horizontal.
- Color para fondos claros, fondos oscuros y fondo transparente.
- Blanco y negro para fondos claros, fondos oscuros y fondo transparente.
- PNG de 256, 512, 1024 y 2048 píxeles: 48 imágenes en total.

## Carpetas

- `assets/icono/` y `assets/logotipo/`: las 48 imágenes.
- `incoming/`: el paquete original (`Draky_Nueva_Identidad_2026.zip`).
- `clip-apertura/`: el clip a pantalla completa que se muestra al abrir las apps Draky.
- `scripts/`: validación y correcciones.

## Correcciones (15-11-2026)

Se hicieron con `scripts/corregir_identidad.py`. Los originales siguen en el ZIP de `incoming/` y en el historial de Git.

- **Iconos (las 24 imágenes):** se quitó un cuadradito suelto que había abajo a la derecha.
- **Iconos de 2048 (6 imágenes):** eran el de 1024 con un margen enorme alrededor, y el dragón ocupaba menos de un tercio. Ahora son el de 1024 ampliado al doble.
- **Logotipo a color con fondo oscuro (4 imágenes):** el texto «Draky Software» era verde muy oscuro y casi no se leía. Ahora es blanco, con la misma forma que en la versión de fondo claro. Las líneas y la hoja siguen en verde.

**Atención:** el flujo «Extraer paquetes de logotipos» vuelve a copiar en `assets/` las imágenes del ZIP cada vez que se sube uno nuevo a `incoming/`. Si se vuelve a subir el paquete original, hay que ejecutar otra vez `scripts/corregir_identidad.py`.

## Calidad

Las imágenes PNG grandes proceden de escalado rasterizado. Todavía no hay un archivo SVG vectorial maestro validado.
