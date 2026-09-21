# Samderbrow - Modpack

Este repositorio contiene el modpack que descarga y sincroniza el launcher Samderbrow.
Incluye `pack.json` (versiones de Minecraft y Forge), los mods en `mods/`, la configuracion en `config/` y las opciones iniciales en `options.txt`.

Despues de cambiar cualquier archivo del pack, corre desde el proyecto del launcher:

```
python generar_manifest.py <esta carpeta>
```

Luego haz commit y push de los cambios (incluyendo el `manifest.json` regenerado) para que el launcher los detecte.
