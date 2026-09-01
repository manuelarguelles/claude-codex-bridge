---
name: indexar-proyecto
description: Archiva la sesión actual en su proyecto (personal o de trabajo) y lo registra en el índice maestro de proyectos. Usar cuando el usuario diga "indexar proyecto", "guardar la sesión", "archivar este proyecto", "/indexar-proyecto", o al cerrar un bloque de trabajo que conviene poder retomar después.
---

# Indexar proyecto (archivar sesión + actualizar índice)

Guarda un resumen recuperable de la sesión actual en la carpeta indicada por `PIDX_HOME` (por defecto `$HOME/clawd/projects-index`) y actualiza el índice maestro. El motor determinista es `pidx.py`; el agente escribe los resúmenes.

**Engine:** `python "$HOME/clawd/projects-index/pidx.py"` (override data home with `PIDX_HOME`).

## Pasos

1. **Identificá el proyecto** (nombre, slug kebab-case, categoría, descripción de 1 línea, tags):
   - **Categoría:** `work` si el trabajo pertenece a un cliente o empleador (por cwd, organización de GitHub o plataforma de datos); `personal` en otro caso (productos propios, demos, experimentos). Si dudás, preguntá.
   - **Slug:** estable y reusable (ej. `data-contract`, `landing-site`). Si el proyecto ya existe en el índice, reusá su slug (corré `pidx.py list` para ver).
   - **Programa vs iniciativa:** si el trabajo es una **iniciativa** de un programa mayor (ej. Plataforma X → v3, dashboards, evaluador), usá la pista `programa:iniciativa` (ej. `plataforma-x:v3-mejoras`). El programa guarda el **contexto compartido** (repos, IDs, tablas, owners, glosario) una sola vez en su `PROGRAM.md`; la iniciativa guarda su objetivo/spec/estado. Si el proyecto es standalone, usá el slug plano como hasta ahora.
   - Argumentos del usuario (`/indexar-proyecto <pista>`) pueden fijar nombre/categoría.

2. **Resolvé la carpeta:** `python "$HOME/clawd/projects-index/pidx.py" path <categoria> <slug-o-programa:iniciativa>` → devuelve la carpeta (la crea con `sessions/`). Para una iniciativa, la carpeta queda anidada en `<categoria>/<programa>/<iniciativa>/`.

3. **Escribí el archivo de sesión** en `<carpeta>/sessions/<YYYY-MM-DD>-<tema-slug>.md` (usá la fecha de hoy). Estructura:
   - **Qué se hizo** (bullets concretos).
   - **Decisiones clave** y por qué.
   - **Artefactos:** PRs/commits/tags, archivos, jobs, URLs (con IDs reales).
   - **Estado actual** (qué quedó funcionando / en prod / pendiente).
   - **Próximos pasos** y **cómo retomar** (comandos, paths, gates/owners).
   - **Transcript crudo:** corré `python "$HOME/clawd/projects-index/pidx.py" transcript` y pegá la ruta del `.jsonl` (sesión completa, por si hace falta el detalle).

4. **Creá o actualizá** `<carpeta>/PROJECT.md` (overview vivo del proyecto, no de esta sesión sola): qué es, arquitectura/repos clave, estado global, links, glosario. Si existe, integrá lo nuevo sin duplicar.

5. **Registrá en el índice:**
   ```
   # Iniciativa de un programa:
   python "$HOME/clawd/projects-index/pidx.py" upsert \
     --name "<Nombre>" --category <work|personal> --slug <iniciativa> \
     --program <programa> --status "<en curso|prod|cerrado|...>" \
     --desc "<una línea>" --tags <a,b,c> --session "<ruta del .md de sesión>"

   # Proyecto standalone (como hasta ahora):
   python "$HOME/clawd/projects-index/pidx.py" upsert \
     --name "<Nombre>" --category <work|personal> --slug <slug> \
     --desc "<una línea>" --tags <a,b,c> --session "<ruta del .md de sesión>"
   ```
   `upsert --program` auto-crea el **stub del programa** si no existe y regenera la tabla de iniciativas del `PROGRAM.md`. Si el programa es nuevo, después completá a mano el **Contexto compartido** del `PROGRAM.md` (repos, IDs, tablas, owners, glosario) — es la parte DRY que las iniciativas referencian.

6. **Reportá:** confirmá el slug, la carpeta, el archivo de sesión y mostrá la fila del índice (`pidx.py get <slug>`).

## Promover una iniciativa a programa

Cuando una iniciativa crece y merece ser un **programa propio** (con sus propias sub-iniciativas), usá:

```
python "$HOME/clawd/projects-index/pidx.py" promote <programa:iniciativa> \
  --into <slug-sub-iniciativa> --into-name "<Nombre legible>" \
  [--program-name "<Nombre del nuevo programa>"] [--dry-run]
```

Qué hace (determinista, opción A):
- Convierte la iniciativa en un **programa nuevo** (hereda nombre/desc/tags).
- Re-aloja **todo su contenido actual** (PROJECT.md + sesiones) en una sub-iniciativa `--into` (default `nucleo`) del nuevo programa — la carpeta se mueve intacta, las sesiones (rutas relativas) sobreviven.
- La saca del programa viejo y regenera `INDEX.md`/`PROGRAM.md`/`index.html`.
- Genera un `PROGRAM.md` **template** para el nuevo programa → **completá a mano el Contexto compartido** (repos, IDs, glosario, links) como en el paso 5.

Buenas prácticas: corré primero `--dry-run`; hacé backup de `index.json` si dudás (`cp index.json index.json.bak`); aborta solo ante colisiones de slug. Después, creá las sub-iniciativas nuevas con `upsert --program <nuevo>` como siempre.

## Dónde va un hallazgo (criterio de destino)

Al archivar, los hallazgos de la sesión se reparten. **Un solo dueño por dato** — los demás
lugares lo referencian con `[[link]]`, nunca lo copian: una copia se desfasa en silencio.

| Tipo de hallazgo | Dónde vive |
|---|---|
| Sirve **en otros proyectos** (gotcha de una librería, límite de una nube, regla de método) | archivo propio en `~/.claude/projects/*/memory/` + **una línea** de hook en `MEMORY.md` |
| Sólo tiene sentido **dentro de este proyecto** (estado, pendientes, decisiones locales) | `PROJECT.md` del proyecto |
| **Decisión con un número que costó medir** | `DECISIONES-MEDIDAS.md` del proyecto, con el script que la reproduce |
| Narrativa de qué pasó hoy | la sesión (`sessions/`), como siempre |

**Regla dura: un hallazgo sin referencia al artefacto que lo produjo (script, corrida, commit,
versión) es una opinión, no un hallazgo.** Anclalo o no lo guardes.

Antes de escribir, buscá si el hallazgo ya existe en `PROJECT.md`, sesiones o memoria local. Si ya está, **enriquecé** el registro existente en vez de duplicarlo.

## Notas
- No reemplaza la auto-memoria (`~/.claude/.../memory/`): esto es archivo explícito de sesiones + índice transversal personal+trabajo, fácil de recuperar con `/recuperar-proyecto`.
- Idempotente: re-indexar el mismo proyecto agrega una sesión nueva y actualiza `updated`/desc/tags; no pisa sesiones anteriores.
- No edites `INDEX.md`/`index.json` a mano — siempre vía `pidx.py upsert`.
