#!/usr/bin/env python3
"""pidx — índice de proyectos con sesiones archivadas (personales y de Apex).

Fuente de verdad: `index.json` en el data home. `INDEX.md` se regenera desde ahí
(vista humana). Determinista: gestiona índice, paths y búsqueda. NO resume sesiones
(eso lo hace Claude vía las skills /indexar-proyecto y /recuperar-proyecto).

Data home: $PIDX_HOME  (default ~/clawd/projects-index)

Uso:
  pidx.py home
  pidx.py path <category> <slug>            # crea (si falta) y devuelve la carpeta del proyecto
  pidx.py upsert --name N --category C --slug S [--desc "..."] [--tags a,b] [--session <ruta.md>] [--date YYYY-MM-DD]
  pidx.py search "<query>"                  # busca en nombre/slug/desc/categoría/tags
  pidx.py get <slug-o-nombre> [-n 5]        # PROJECT.md + sesiones recientes
  pidx.py list [--category C]
  pidx.py transcript [--cwd <dir>]          # ruta del .jsonl de la sesión actual (best-effort)
"""
import os, sys, re, json, argparse, datetime, shutil
from pathlib import Path

HOME = Path(os.environ.get("PIDX_HOME", str(Path.home() / "clawd" / "projects-index")))
IDX = HOME / "index.json"


def _today():
    return datetime.date.today().isoformat()


def _parse_ident(ident):
    """'programa:iniciativa' -> ('programa','iniciativa'); 'slug' -> (None,'slug')."""
    if ident and ":" in ident:
        prog, _, init = ident.partition(":")
        return prog.strip(), init.strip()
    return None, (ident or "").strip()


def _is_program(p):
    return p.get("kind") == "program"


# --- Nivel 3: entregables -----------------------------------------------------
# Jerarquía: programa → iniciativa → ENTREGABLE.
# Un entregable = la cosa concreta que se termina y se publica. Vive ANIDADO en la
# iniciativa (no como proyecto propio) para no explotar el índice: una idea con 5
# salidas seguiría siendo 1 fila, no 6.
# `destino` es un CAMPO del entregable, no un nivel: así el mismo esquema sirve para
# contenido (destino=LinkedIn/TikTok/blog) y para trabajo técnico (destino=repo/Confluence),
# donde "canal" no significaría nada.
def _deliv(p):
    return p.setdefault("entregables", [])


def _fmt_deliv(d):
    dest = f" → {d['destino']}" if d.get("destino") else ""
    est = f" [{d['estado']}]" if d.get("estado") else ""
    return f"{d['nombre']}{dest}{est}"


def _folder_for(p):
    cat = p.get("category", "personal")
    if p.get("program"):
        return f"{cat}/{p['program']}/{p['slug']}"
    return f"{cat}/{p['slug']}"


def _load():
    if IDX.exists():
        return json.loads(IDX.read_text(encoding="utf-8"))
    return {"projects": []}


def _render_md(data):
    lines = [
        "# Índice de Proyectos", "",
        "_Generado por `pidx.py` — no editar a mano (usá `pidx.py upsert`)._", "",
        "| Proyecto | Categoría | Slug | Descripción | Tags | Últ. sesión | # | Carpeta |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in data["projects"]:
        desc = (p.get("desc", "") or "").replace("|", "\\|")
        lines.append("| {n} | {c} | `{s}` | {d} | {t} | {u} | {k} | `{f}` |".format(
            n=p.get("name", ""), c=p.get("category", ""), s=p.get("slug", ""),
            d=desc[:100], t=", ".join(p.get("tags", [])), u=p.get("updated", ""),
            k=len(p.get("sessions", [])), f=p.get("folder", "")))
    (HOME / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


PROG_START = "<!-- pidx:initiatives -->"
PROG_END = "<!-- /pidx:initiatives -->"


def _deliv_lines(c):
    """Sub-filas de entregables bajo cada iniciativa en la tabla del PROGRAM.md."""
    out = []
    for d in c.get("entregables", []):
        dest = f" → `{d['destino']}`" if d.get("destino") else ""
        est = (d.get("estado", "") or "").replace("|", "\\|")
        url = f"[ver]({d['url']})" if d.get("url") else ""
        # mismas columnas que la fila de la iniciativa: qué es | estado | link | —
        out.append(f"| ↳ {d['nombre']}{dest} | {est} | {url} |  |")
    return out


def _initiatives_block(data, prog_slug):
    kids = sorted([c for c in data["projects"] if c.get("program") == prog_slug],
                  key=lambda c: c.get("slug", ""))
    lines = [PROG_START,
             "| Iniciativa | Estado | Objetivo | Últ. sesión |",
             "|---|---|---|---|"]
    for c in kids:
        desc = (c.get("desc", "") or "").replace("|", "\\|")[:80]
        lines.append(f"| `{c['slug']}` | {c.get('status', '')} | {desc} | {c.get('updated', '')} |")
        lines += _deliv_lines(c)
    lines.append(PROG_END)
    return "\n".join(lines)


def _write_program_md(data, prog):
    folder = HOME / _folder_for(prog)
    folder.mkdir(parents=True, exist_ok=True)
    pm = folder / "PROGRAM.md"
    block = _initiatives_block(data, prog["slug"])
    if pm.exists():
        txt = pm.read_text(encoding="utf-8")
        if PROG_START in txt and PROG_END in txt:
            pre = txt.split(PROG_START)[0]
            post = txt.split(PROG_END, 1)[1]
            pm.write_text(pre + block + post, encoding="utf-8")
        else:
            pm.write_text(txt.rstrip() + "\n\n## Iniciativas\n" + block + "\n", encoding="utf-8")
    else:
        pm.write_text(
            f"# {prog.get('name', prog['slug'])}\n\n"
            f"> Programa. El contexto compartido va abajo; la tabla de iniciativas se auto-genera.\n\n"
            f"## Contexto compartido\n_(completar: repos, IDs clave, tablas, owners, glosario, links)_\n\n"
            f"## Iniciativas\n{block}\n", encoding="utf-8")


def _html_escape(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _render_html(data):
    progs = [p for p in data["projects"] if _is_program(p)]
    standalone = [p for p in data["projects"] if not p.get("kind") and not p.get("program")]
    n_init = len([p for p in data["projects"] if p.get("program")])
    cards = []
    for pr in sorted(progs, key=lambda p: p["slug"]):
        kids = sorted([c for c in data["projects"] if c.get("program") == pr["slug"]], key=lambda c: c["slug"])
        rows = "".join(
            f"<tr data-status='{_html_escape(c.get('status',''))}'>"
            f"<td><code>{_html_escape(pr['slug'])}:{_html_escape(c['slug'])}</code> {_html_escape(c.get('name',''))}</td>"
            f"<td><span class='badge'>{_html_escape(c.get('status','') or '—')}</span></td>"
            f"<td>{_html_escape(c.get('desc',''))}</td>"
            f"<td>{_html_escape(c.get('updated',''))}</td></tr>" for c in kids)
        cards.append(
            f"<section class='card' data-cat='{_html_escape(pr.get('category',''))}'>"
            f"<h2>▸ {_html_escape(pr.get('name', pr['slug']))} "
            f"<small>[{_html_escape(pr.get('category',''))}]</small></h2>"
            f"<p class='desc'>{_html_escape(pr.get('desc',''))}</p>"
            f"<table><thead><tr><th>Iniciativa</th><th>Estado</th><th>Objetivo</th><th>Últ.</th></tr></thead>"
            f"<tbody>{rows or '<tr><td colspan=4><em>sin iniciativas</em></td></tr>'}</tbody></table></section>")
    st_rows = "".join(
        f"<tr data-cat='{_html_escape(p.get('category',''))}'>"
        f"<td><code>{_html_escape(p['slug'])}</code> {_html_escape(p.get('name',''))}</td>"
        f"<td>{_html_escape(p.get('category',''))}</td>"
        f"<td>{_html_escape(p.get('desc',''))}</td>"
        f"<td>{_html_escape(p.get('updated',''))}</td></tr>"
        for p in sorted(standalone, key=lambda p: (p.get('category',''), p['slug'])))
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Índice de Proyectos</title>
<style>
:root{{color-scheme:light dark}}
body{{font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;max-width:1100px;margin:0 auto;padding:24px;
background:#0e1116;color:#e6edf3;line-height:1.5}}
@media (prefers-color-scheme: light){{body{{background:#f6f8fa;color:#1f2328}}}}
h1{{font-size:1.5rem}} h2{{font-size:1.1rem;margin:.2rem 0}}
.meta{{opacity:.7;font-size:.9rem;margin-bottom:1rem}}
.card{{border:1px solid #30363d;border-radius:10px;padding:14px 18px;margin:14px 0;background:#161b22}}
@media (prefers-color-scheme: light){{.card{{background:#fff;border-color:#d0d7de}}}}
.desc{{opacity:.8;margin:.2rem 0 .6rem}}
table{{width:100%;border-collapse:collapse;font-size:.92rem}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid #30363d;vertical-align:top}}
th{{opacity:.6;font-weight:600}}
code{{background:#30363d5c;padding:1px 5px;border-radius:5px}}
.badge{{background:#1f6feb33;color:#79c0ff;padding:1px 8px;border-radius:999px;font-size:.82rem;white-space:nowrap}}
</style></head><body>
<h1>Índice de Proyectos</h1>
<div class="meta">{len(progs)} programas · {n_init} iniciativas · {len(standalone)} standalone — generado por pidx</div>
{''.join(cards)}
<section class="card"><h2>Standalone</h2>
<table><thead><tr><th>Slug</th><th>Categoría</th><th>Descripción</th><th>Últ.</th></tr></thead>
<tbody>{st_rows or '<tr><td colspan=4><em>—</em></td></tr>'}</tbody></table></section>
</body></html>"""
    (HOME / "index.html").write_text(html, encoding="utf-8")


def _save(data):
    HOME.mkdir(parents=True, exist_ok=True)
    data["projects"].sort(key=lambda p: (p.get("category", ""), p.get("program", "") or "", p.get("slug", "")))
    IDX.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _render_md(data)
    for p in data["projects"]:
        if _is_program(p):
            _write_program_md(data, p)
    _render_html(data)


def _find(data, ident):
    prog, slug = _parse_ident(ident)
    sl = slug.lower()
    if prog:
        pl = prog.lower()
        for p in data["projects"]:
            if p.get("slug", "").lower() == sl and (p.get("program", "") or "").lower() == pl:
                return p
        return None
    for p in data["projects"]:
        if p.get("slug", "").lower() == sl or p.get("name", "").lower() == sl:
            return p
    return None


def cmd_home(a):
    print(HOME)


def cmd_path(a):
    prog, slug = _parse_ident(a.slug)
    folder = HOME / a.category / prog / slug if prog else HOME / a.category / slug
    (folder / "sessions").mkdir(parents=True, exist_ok=True)
    print(folder)


def cmd_upsert(a):
    data = _load()
    ident = f"{a.program}:{a.slug}" if a.program else a.slug
    p = _find(data, ident)
    if not p:
        p = {"slug": a.slug, "sessions": []}
        data["projects"].append(p)
    p["name"] = a.name or p.get("name", a.slug)
    p["category"] = a.category or p.get("category", "personal")
    if a.kind:
        p["kind"] = a.kind
    if a.program:
        p["program"] = a.program
        p["kind"] = "initiative"
        if not _find(data, a.program):
            data["projects"].append({
                "slug": a.program, "name": a.program, "category": p["category"],
                "kind": "program", "desc": "", "tags": [], "sessions": [],
                "folder": f"{p['category']}/{a.program}", "updated": a.date or _today()})
    if a.desc:
        p["desc"] = a.desc
    if a.tags:
        p["tags"] = [t.strip() for t in a.tags.split(",") if t.strip()]
    if a.status:
        p["status"] = a.status
    p.setdefault("desc", "")
    p.setdefault("tags", [])
    p["folder"] = _folder_for(p)
    p["updated"] = a.date or _today()
    (HOME / p["folder"] / "sessions").mkdir(parents=True, exist_ok=True)
    if a.session:
        s = a.session
        if os.path.isabs(s) and s.startswith(str(HOME)):
            s = os.path.relpath(s, HOME / p["folder"])
        if s not in p["sessions"]:
            p["sessions"].append(s)
    _save(data)
    print(f"OK: {p['name']} [{p['category']}] -> {HOME / p['folder']}  (sesiones: {len(p['sessions'])})")


def cmd_search(a):
    data = _load()
    q = a.query.lower()
    hits = [p for p in data["projects"] if q in " ".join([
        p.get("name", ""), p.get("slug", ""), p.get("desc", ""),
        p.get("category", ""), " ".join(p.get("tags", []))]).lower()]
    if not hits:
        print(f"(sin matches para {a.query!r}). Probá `pidx.py list`.")
        return
    for p in hits:
        print(f"- {p['slug']}  [{p['category']}]  {p['name']}  — {p.get('desc','')[:80]}  ({HOME / p['folder']})")


def cmd_get(a):
    data = _load()
    p = _find(data, a.ident)
    if not p:
        cmd_search(argparse.Namespace(query=a.ident))
        return
    folder = HOME / p["folder"]
    print(f"# {p['name']}  [{p['category']}]")
    print(f"slug: {p['slug']} | kind: {p.get('kind', 'standalone')} | updated: {p.get('updated', '')} | tags: {', '.join(p.get('tags', []))}")
    print(f"folder: {folder}")
    if _is_program(p):
        pm = folder / "PROGRAM.md"
        print(f"PROGRAM.md: {pm}  ({'existe' if pm.exists() else 'NO existe'})")
        kids = sorted([c for c in data["projects"] if c.get("program") == p["slug"]], key=lambda c: c["slug"])
        print(f"iniciativas ({len(kids)}):")
        for c in kids:
            nd = len(c.get("entregables", []))
            extra = f" · {nd} entregable(s)" if nd else ""
            print(f"  - {p['slug']}:{c['slug']}  [{c.get('status', '')}]  {c.get('name', '')}  ({len(c.get('sessions', []))} ses.{extra})")
        return
    if p.get("program"):
        prog_pm = HOME / p["category"] / p["program"] / "PROGRAM.md"
        print(f"programa: {p['program']} | contexto compartido: {prog_pm}")
    ents = p.get("entregables", [])
    if ents:
        print(f"entregables ({len(ents)}):")
        for d in ents:
            url = f"  {d['url']}" if d.get("url") else ""
            print(f"  - {_fmt_deliv(d)}{url}")
    pm = folder / "PROJECT.md"
    print(f"PROJECT.md: {pm}  ({'existe' if pm.exists() else 'NO existe'})")
    sess = sorted((folder / "sessions").glob("*.md")) if (folder / "sessions").exists() else []
    print(f"sesiones ({len(sess)}):")
    for s in sess[-a.n:]:
        print(f"  - {s}")


def cmd_list(a):
    data = _load()
    for p in data["projects"]:
        if a.category and p.get("category") != a.category:
            continue
        if _is_program(p):
            print(f"▸ {p['slug']}  [{p['category']}]  {p['name']}  (programa)")
            kids = sorted([c for c in data["projects"] if c.get("program") == p["slug"]], key=lambda c: c["slug"])
            for c in kids:
                print(f"    - {p['slug']}:{c['slug']}  [{c.get('status', '')}]  {c['name']}  ({len(c.get('sessions', []))} ses.)")
        elif not p.get("program"):
            print(f"- {p['slug']}  [{p['category']}]  {p['name']}  ({len(p.get('sessions', []))} ses.)")


def cmd_transcript(a):
    """Ruta del .jsonl de la sesión actual (best-effort): el más reciente del dir
    de proyecto de Claude Code que matchea el cwd codificado."""
    cwd = a.cwd or os.getcwd()
    enc = re.sub(r"[^a-zA-Z0-9]", "-", cwd)
    base = Path.home() / ".claude" / "projects"
    d = base / enc
    if not d.exists():
        cands = [c for c in base.glob("*" + re.sub(r"[^a-zA-Z0-9]", "-", Path(cwd).name) + "*") if c.is_dir()]
        d = cands[0] if cands else None
    if not d or not d.exists():
        print("(no se encontró el dir de transcripts para este cwd)", file=sys.stderr)
        sys.exit(1)
    jsonls = sorted(d.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not jsonls:
        print("(sin .jsonl en el dir de transcripts)", file=sys.stderr)
        sys.exit(1)
    print(jsonls[0])


def cmd_promote(a):
    """Promueve una INICIATIVA a PROGRAMA propio (opción A).

    El contenido actual de la iniciativa (PROJECT.md + sesiones) se re-aloja en una
    sub-iniciativa `--into` (default 'nucleo') del nuevo programa, cuya carpeta se
    mueve intacta (las sesiones son rutas relativas, sobreviven el move). El nodo
    programa hereda nombre/desc/tags. PROGRAM.md se genera como template para que
    Claude complete el contexto compartido. Idempotencia: aborta ante colisiones.
    """
    data = _load()
    node = _find(data, a.ident)
    if not node:
        print(f"(no encontré '{a.ident}')", file=sys.stderr); sys.exit(1)
    if node.get("kind") != "initiative" or not node.get("program"):
        print(f"'{a.ident}' no es una iniciativa dentro de un programa "
              f"(kind={node.get('kind')}, program={node.get('program')}).", file=sys.stderr)
        sys.exit(1)
    cat = node.get("category", "personal")
    old_program = node["program"]
    new_prog_slug = node["slug"]
    into_slug = (a.into or "nucleo").strip()
    into_name = a.into_name or node.get("name", into_slug)
    program_name = a.program_name or node.get("name", new_prog_slug)

    for p in data["projects"]:
        if p is node:
            continue
        if p.get("slug", "").lower() == new_prog_slug.lower() and _is_program(p):
            print(f"Ya existe un programa con slug '{new_prog_slug}'.", file=sys.stderr); sys.exit(1)
        if (p.get("slug", "").lower() == into_slug.lower()
                and (p.get("program", "") or "").lower() == new_prog_slug.lower()):
            print(f"Ya existe la iniciativa '{new_prog_slug}:{into_slug}'.", file=sys.stderr); sys.exit(1)

    old_folder = HOME / cat / old_program / node["slug"]
    new_prog_folder = HOME / cat / new_prog_slug
    into_folder = new_prog_folder / into_slug

    if a.dry_run:
        print(f"[dry-run] {old_program}:{new_prog_slug}  →  programa '{new_prog_slug}'")
        print(f"[dry-run]   contenido previo  →  iniciativa '{new_prog_slug}:{into_slug}' ({into_name})")
        print(f"[dry-run]   mover  {old_folder}")
        print(f"[dry-run]       →  {into_folder}")
        return

    if into_folder.exists():
        print(f"El destino ya existe: {into_folder}", file=sys.stderr); sys.exit(1)
    new_prog_folder.mkdir(parents=True, exist_ok=True)
    if old_folder.exists():
        shutil.move(str(old_folder), str(into_folder))
    else:
        (into_folder / "sessions").mkdir(parents=True, exist_ok=True)

    # nodo existente -> re-alojado como sub-iniciativa
    node["slug"] = into_slug
    node["name"] = into_name
    node["program"] = new_prog_slug
    node["kind"] = "initiative"
    node["folder"] = f"{cat}/{new_prog_slug}/{into_slug}"
    node["updated"] = a.date or _today()

    # nuevo nodo programa (hereda identidad hacia arriba)
    data["projects"].append({
        "slug": new_prog_slug, "name": program_name, "category": cat, "kind": "program",
        "desc": node.get("desc", ""), "tags": node.get("tags", []), "sessions": [],
        "folder": f"{cat}/{new_prog_slug}", "updated": a.date or _today()})

    _save(data)
    print(f"OK: promovido {old_program}:{new_prog_slug}  →  programa '{new_prog_slug}'")
    print(f"    contenido previo  →  iniciativa '{new_prog_slug}:{into_slug}' ({into_name})")
    print(f"    carpeta: {new_prog_folder}")
    print(f"    PROGRAM.md generado (template) — completá el contexto compartido.")


def cmd_entregable(a):
    """Alta/actualización de un ENTREGABLE (nivel 3) dentro de una iniciativa.

    Idempotente por `nombre`: si ya existe, actualiza solo los campos pasados.
    Ej:  pidx entregable infografias-linkedin:6m-ia --nombre "infografia" \
             --destino LinkedIn --estado publicada --url https://...
    """
    data = _load()
    ident = a.ident if ":" in a.ident else (f"{a.program}:{a.ident}" if a.program else a.ident)
    p = _find(data, ident)
    if not p:
        print(f"✗ no existe la iniciativa: {ident}")
        raise SystemExit(1)
    if _is_program(p):
        print(f"✗ {ident} es un PROGRAMA. Los entregables cuelgan de una iniciativa.")
        raise SystemExit(1)

    ents = _deliv(p)
    if a.rm:
        n = len(ents)
        p["entregables"] = [d for d in ents if d["nombre"] != a.rm]
        print(f"{'✓ eliminado' if len(p['entregables']) < n else '✗ no encontrado'}: {a.rm}")
    else:
        if not a.nombre:
            print("✗ falta --nombre (o usá --rm para eliminar)")
            raise SystemExit(1)
        d = next((x for x in ents if x["nombre"] == a.nombre), None)
        if not d:
            d = {"nombre": a.nombre}
            ents.append(d)
        for k in ("destino", "estado", "url"):
            v = getattr(a, k, None)
            if v:
                d[k] = v
        print(f"✓ {_fmt_deliv(d)}")

    p["updated"] = a.date or _today()
    _save(data)
    if p.get("program"):
        prog = _find(data, p["program"])
        if prog:
            _write_program_md(data, prog)
    print(f"  {len(p.get('entregables', []))} entregable(s) en {ident}")


def main():
    ap = argparse.ArgumentParser(prog="pidx")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("home")
    pp = sub.add_parser("path"); pp.add_argument("category"); pp.add_argument("slug")
    pu = sub.add_parser("upsert")
    pu.add_argument("--name"); pu.add_argument("--category"); pu.add_argument("--slug", required=True)
    pu.add_argument("--desc"); pu.add_argument("--tags"); pu.add_argument("--session"); pu.add_argument("--date")
    pu.add_argument("--program"); pu.add_argument("--kind"); pu.add_argument("--status")
    ps = sub.add_parser("search"); ps.add_argument("query")
    pg = sub.add_parser("get"); pg.add_argument("ident"); pg.add_argument("-n", type=int, default=5)
    pl = sub.add_parser("list"); pl.add_argument("--category")
    pt = sub.add_parser("transcript"); pt.add_argument("--cwd")
    pr = sub.add_parser("promote")
    pr.add_argument("ident", help="programa:iniciativa a promover")
    pr.add_argument("--into", help="slug de la sub-iniciativa que hereda el contenido actual (default 'nucleo')")
    pr.add_argument("--into-name", help="nombre legible de esa sub-iniciativa")
    pr.add_argument("--program-name", help="nombre del nuevo programa (default: el de la iniciativa)")
    pr.add_argument("--date")
    pr.add_argument("--dry-run", action="store_true")
    pe = sub.add_parser("entregable", help="nivel 3: entregable de una iniciativa (destino = campo)")
    pe.add_argument("ident", help="programa:iniciativa")
    pe.add_argument("--program", help="alternativa a usar programa:iniciativa")
    pe.add_argument("--nombre", help="qué es (infografia, paper, reel, PR #115...)")
    pe.add_argument("--destino", help="dónde va (LinkedIn, blog, TikTok, repo, Confluence...)")
    pe.add_argument("--estado")
    pe.add_argument("--url")
    pe.add_argument("--rm", help="eliminar el entregable con ese nombre")
    pe.add_argument("--date")

    a = ap.parse_args()
    {"home": cmd_home, "path": cmd_path, "upsert": cmd_upsert, "search": cmd_search,
     "get": cmd_get, "list": cmd_list, "transcript": cmd_transcript,
     "promote": cmd_promote, "entregable": cmd_entregable}[a.cmd](a)


if __name__ == "__main__":
    main()
