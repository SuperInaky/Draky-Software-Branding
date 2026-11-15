#!/usr/bin/env python3
"""Validate and index the original Draky Software PNG deliverables.
This script NEVER resizes or recreates approved artwork.
"""
from pathlib import Path
from PIL import Image
import json
import sys

root=Path("assets")
sizes={256,512,1024,2048}
variants=["Color_Fondo_Claro","Color_Fondo_Oscuro","Color_Transparente","Blanco_Negro_Fondo_Claro","Blanco_Negro_Fondo_Oscuro","Blanco_Negro_Transparente"]
report={"files":[],"missing":[],"errors":[]}
for family,folder in [("Icono","icono"),("Logotipo","logotipo")]:
    for variant in variants:
        for size in sorted(sizes):
            name=f"{family}_{variant}_{size}.png"
            p=root/folder/name
            if not p.is_file():
                report["missing"].append(str(p))
                continue
            try:
                with Image.open(p) as im:
                    im.verify()
                with Image.open(p) as im:
                    width,height=im.size
                    expected_height = size if family == 'Icono' else size // 2
                    if width != size or height != expected_height:
                        report["errors"].append(f"{p}: dimensions {width}x{height} != {size}x{expected_height}")
                    report["files"].append({"path":str(p),"width":width,"height":height,"bytes":p.stat().st_size})
            except Exception as exc:
                report["errors"].append(f"{p}: {exc}")
Path("assets").mkdir(exist_ok=True)
Path("assets/manifest.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(f"Validated {len(report['files'])}/48 PNGs, missing {len(report['missing'])}, errors {len(report['errors'])}")
if report["missing"] or report["errors"]:
    sys.exit(1)
