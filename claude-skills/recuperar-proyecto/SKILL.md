---
name: recuperar-proyecto
description: Recupera el contexto de un proyecto archivado (personal o Apex) desde el índice maestro, para retomar el trabajo. Usar cuando el usuario diga "recuperar proyecto <nombre>", "retomar <proyecto>", "traé el contexto de <proyecto>", "/recuperar-proyecto <nombre/contexto>", o pregunte en qué quedó un proyecto.
---

# Recuperar proyecto (cargar contexto desde el índice)

Busca un proyecto en el índice maestro indicado por `PIDX_HOME` (por defecto `$HOME/clawd/projects-index`) y carga su contexto (overview + sesiones recientes) para poder retomar.

**Engine:** `python "$HOME/clawd/projects-index/pidx.py"` (override data home with `PIDX_HOME`).

## Pasos

1. **Tomá la pista del usuario** (`/recuperar-proyecto <nombre o contexto>`). Si no pasó nada, mostrá el catálogo: `python "$HOME/clawd/projects-index/pidx.py" list`.

2. **Buscá:** `python "$HOME/clawd/projects-index/pidx.py" search "<pista>"`.
   - Si hay **varios** matches, listalos (slug, categoría, nombre, desc) y preguntá cuál.
   - Si hay **uno** claro, seguí con su slug.

3. **Traé los punteros:** `python "$HOME/clawd/projects-index/pidx.py" get <slug|programa|programa:iniciativa> -n 5`.
   - Si es un **programa**, devuelve el `PROGRAM.md` + la lista de iniciativas con su estado.
   - Si es una **iniciativa** (`programa:iniciativa`), devuelve el `PROJECT.md` de la iniciativa, sus sesiones, y el puntero al `PROGRAM.md` del programa (contexto compartido).

4. **Cargá el contexto:**
   - **Programa:** leé el `PROGRAM.md` (contexto compartido + tabla de iniciativas). Presentá el panorama y preguntá en qué iniciativa seguir.
   - **Iniciativa:** leé PRIMERO la sección **Contexto compartido** del `PROGRAM.md` del programa (resumida), y luego el `PROJECT.md` de la iniciativa + su(s) sesión(es) reciente(s). Para el detalle fino, abrí el `.jsonl` referenciado en la sesión.
   - **Standalone:** leé `PROJECT.md` + sesión(es) reciente(s), como hasta ahora.

5. **Resumí y ofrecé retomar:** presentá al usuario, conciso:
   - Qué es el proyecto y su estado actual.
   - Qué quedó pendiente / próximos pasos.
   - Cómo retomar (comandos/paths/owners relevantes).
   Y preguntá por dónde quiere seguir.

## Notas
- Si el `search` no devuelve nada, probá `pidx.py list` y ofrecé las opciones más cercanas.
- Es de solo lectura: recuperar NO modifica el índice. Para guardar avances nuevos, usá `/indexar-proyecto`.
