import os

# Repositorio público de GitHub con el modpack
REPO_DUENO = "samechp"
REPO_NOMBRE = "samderbrow-modpack"
REPO_RAMA = "main"

CARPETA_JUEGO = os.path.join(os.environ["APPDATA"], ".samderbrow")

# Espejo: queda exactamente igual que en GitHub (borra lo que sobra)
CARPETAS_ESPEJO = ("mods", "resourcepacks", "shaderpacks")
# Pisar: descarga lo nuevo o cambiado, nunca borra
CARPETAS_PISAR = ("config",)
# Inicial: solo se descarga si no existe
ARCHIVOS_INICIALES = ("options.txt",)

RAM_MIN = 2
RAM_POR_DEFECTO = 6
RAM_TOPE = 32
