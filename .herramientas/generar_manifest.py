"""Herramienta del dueño del pack.

Uso:  python generar_manifest.py C:/ruta/al/repositorio/modpack
Córrela cada vez que cambies algo del pack, antes de hacer commit y push.

Los archivos de más de 100 MB no caben en GitHub: ponlos en externos.json
({"mods/archivo.jar": "https://cdn.modrinth.com/..."}) y en el .gitignore del pack;
el launcher los baja de esa dirección.
"""
import json
import os
import sys

from sincronizar import escanear_locales, ruta_es_valida

LIMITE_GITHUB = 100 * 1024 * 1024


def leer_externos(carpeta_pack):
    camino = os.path.join(carpeta_pack, "externos.json")
    if not os.path.isfile(camino):
        return {}
    with open(camino, encoding="utf-8") as f:
        return json.load(f)


def generar(carpeta_pack):
    externos = leer_externos(carpeta_pack)
    archivos = []
    for ruta, sha1 in sorted(escanear_locales(carpeta_pack).items()):
        if not ruta_es_valida(ruta):
            print(f"Ignorado (nombre no válido): {ruta}")
            continue
        tamano = os.path.getsize(os.path.join(carpeta_pack, *ruta.split("/")))
        entrada = {"ruta": ruta, "sha1": sha1, "tamano": tamano}
        if ruta in externos:
            entrada["url"] = externos[ruta]
        archivos.append(entrada)
    return {"archivos": archivos}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    carpeta_pack = argv[0] if argv else "."

    if not os.path.isfile(os.path.join(carpeta_pack, ".gitattributes")):
        print("AVISO: falta .gitattributes con la línea '* -text'. Sin él, git puede "
              "cambiar los saltos de línea de la config y las descargas fallarán.")

    manifiesto = generar(carpeta_pack)
    for a in manifiesto["archivos"]:
        if a["tamano"] > LIMITE_GITHUB and "url" not in a:
            print(f"AVISO: {a['ruta']} pesa más de 100 MB y no cabe en GitHub. "
                  "Agrega su enlace de Modrinth a externos.json y el archivo al .gitignore del pack.")
    with open(os.path.join(carpeta_pack, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, indent=2, ensure_ascii=False)
    print(f"manifest.json generado con {len(manifiesto['archivos'])} archivos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
