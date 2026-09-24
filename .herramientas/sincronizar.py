import hashlib
import os
import re
from dataclasses import dataclass, field

from ajustes import ARCHIVOS_INICIALES, CARPETAS_AJENAS, CARPETAS_ESPEJO, CARPETAS_PISAR

_RESERVADOS = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
_SHA1 = re.compile(r"[0-9a-fA-F]{40}")
PREFIJO_URL_EXTERNA = "https://cdn.modrinth.com/"


def es_ajena(ruta):
    """True si la ruta la maneja un mod (por ejemplo el navegador que baja MCEF) y no el launcher."""
    return any(ruta == c or ruta.startswith(c + "/") for c in CARPETAS_AJENAS)


def regla_de(ruta):
    """Qué regla aplica a una ruta del pack: "espejo", "pisar", "inicial" o None."""
    if es_ajena(ruta):
        return None
    partes = ruta.split("/")
    if len(partes) == 1:
        return "inicial" if ruta in ARCHIVOS_INICIALES else None
    if partes[0] in CARPETAS_ESPEJO:
        return "espejo"
    if partes[0] in CARPETAS_PISAR:
        return "pisar"
    return None


def _segmento_valido(parte):
    if parte.endswith(".") or parte.endswith(" "):
        return False
    nombre = parte.split(".", 1)[0]
    return nombre.upper() not in _RESERVADOS


def ruta_es_valida(ruta):
    """True si la ruta es relativa, limpia y cae en una carpeta o archivo gestionado."""
    if not isinstance(ruta, str) or not ruta:
        return False
    if "\\" in ruta or ":" in ruta or ruta.startswith("/"):
        return False
    partes = ruta.split("/")
    if any(parte in ("", ".", "..") for parte in partes):
        return False
    if not all(_segmento_valido(parte) for parte in partes):
        return False
    return regla_de(ruta) is not None


def sha1_de_archivo(camino):
    h = hashlib.sha1()
    with open(camino, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def escanear_locales(carpeta):
    """Devuelve {ruta con "/": sha1} de todo lo gestionado que existe en `carpeta`."""
    locales = {}
    for nombre_carpeta in CARPETAS_ESPEJO + CARPETAS_PISAR:
        for raiz, _, archivos in os.walk(os.path.join(carpeta, nombre_carpeta)):
            for nombre in archivos:
                camino = os.path.join(raiz, nombre)
                ruta = os.path.relpath(camino, carpeta).replace(os.sep, "/")
                if es_ajena(ruta):
                    continue
                locales[ruta] = sha1_de_archivo(camino)
    for ruta in ARCHIVOS_INICIALES:
        camino = os.path.join(carpeta, ruta)
        if os.path.isfile(camino):
            locales[ruta] = sha1_de_archivo(camino)
    return locales


@dataclass
class Plan:
    descargar: list = field(default_factory=list)
    borrar: list = field(default_factory=list)
    rechazadas: list = field(default_factory=list)


def validar_manifiesto(manifiesto):
    """None si `manifiesto` tiene la forma esperada; ValueError si no."""
    if not isinstance(manifiesto, dict) or not isinstance(manifiesto.get("archivos"), list):
        raise ValueError("manifest.json inválido: falta la lista 'archivos'")
    for entrada in manifiesto["archivos"]:
        if not isinstance(entrada, dict):
            raise ValueError("manifest.json inválido: cada entrada debe ser un objeto")
        ruta, sha1, tamano = entrada.get("ruta"), entrada.get("sha1"), entrada.get("tamano")
        if not isinstance(ruta, str):
            raise ValueError("manifest.json inválido: 'ruta' debe ser texto")
        if not isinstance(sha1, str) or not _SHA1.fullmatch(sha1):
            raise ValueError(f"manifest.json inválido: sha1 inválido en {ruta!r}")
        if not isinstance(tamano, int) or isinstance(tamano, bool):
            raise ValueError(f"manifest.json inválido: 'tamano' debe ser entero en {ruta!r}")
        # Los archivos que no caben en GitHub (más de 100 MB) se bajan de Modrinth
        url = entrada.get("url")
        if url is not None and (not isinstance(url, str) or not url.startswith(PREFIJO_URL_EXTERNA)):
            raise ValueError(f"manifest.json inválido: url no permitida en {ruta!r}")
        entrada["sha1"] = sha1.lower()


def _protegido_de_borrado(ruta):
    """settings por-shader de Oculus/Iris: nunca se borran aunque shaderpacks sea espejo."""
    partes = ruta.split("/")
    return partes[0] == "shaderpacks" and ruta.lower().endswith(".txt")


def planificar(manifiesto, locales):
    validar_manifiesto(manifiesto)
    plan = Plan()
    remotos = {}
    for archivo in manifiesto["archivos"]:
        if ruta_es_valida(archivo.get("ruta")):
            remotos[archivo["ruta"]] = archivo
        else:
            plan.rechazadas.append(archivo.get("ruta"))

    locales_por_casefold = {}
    for ruta, sha in locales.items():
        locales_por_casefold.setdefault(ruta.casefold(), sha)

    for ruta, archivo in sorted(remotos.items()):
        sha_local = locales.get(ruta)
        if sha_local is None:
            sha_local = locales_por_casefold.get(ruta.casefold())
        if regla_de(ruta) == "inicial":
            if sha_local is None:
                plan.descargar.append(archivo)
        elif sha_local != archivo["sha1"]:
            plan.descargar.append(archivo)

    remotos_casefold = {ruta.casefold() for ruta in remotos}
    plan.borrar = sorted(
        ruta for ruta in locales
        if regla_de(ruta) == "espejo"
        and ruta.casefold() not in remotos_casefold
        and not _protegido_de_borrado(ruta)
    )
    return plan


class ErrorDescarga(Exception):
    pass


def ruta_local(carpeta, ruta):
    """Camino absoluto de `ruta` dentro de `carpeta`. ValueError si se sale de ella."""
    base = os.path.realpath(carpeta)
    camino = os.path.realpath(os.path.join(base, *ruta.split("/")))
    if camino == base or os.path.commonpath([base, camino]) != base:
        raise ValueError(f"Ruta fuera de la carpeta del juego: {ruta!r}")
    return camino


def _sin_aviso(texto, hechos, total):
    pass


def ejecutar_plan(plan, carpeta, descargar, avisar=_sin_aviso):
    """Descarga y verifica todo lo del plan; solo si todo salió bien, borra los sobrantes."""
    total = len(plan.descargar)
    for hechos, archivo in enumerate(plan.descargar):
        ruta = archivo["ruta"]
        avisar(f"Descargando {ruta} ({hechos + 1}/{total})", hechos, total)
        destino = ruta_local(carpeta, ruta)
        temporal = destino + ".tmp"
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        try:
            for _ in range(2):
                descargar(ruta, temporal)
                if sha1_de_archivo(temporal) == archivo["sha1"]:
                    break
            else:
                raise ErrorDescarga(f"El archivo {ruta} llegó dañado")
            os.replace(temporal, destino)
        finally:
            if os.path.exists(temporal):
                os.remove(temporal)

    for ruta in plan.borrar:
        try:
            os.remove(ruta_local(carpeta, ruta))
        except FileNotFoundError:
            pass

    avisar("Archivos al día", total, total)
