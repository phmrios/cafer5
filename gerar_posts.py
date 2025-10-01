# gerar_posts.py — versão com chaves do CSS escapadas nos templates
import json, re, pathlib, unicodedata, html
from datetime import datetime

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "content"
OUT_JSON = ROOT / "posts.json"
OUT_DIR = ROOT / "posts"
SITE_TITLE = "Pedro Rios — Blog sobre café, aprendizados e experimentos"
BASE_CANONICAL = "http://localhost:8000"  # ajuste quando publicar

MD_META_RE = re.compile(r'^(tag|title|description|datePublished|slug):\s*(.+)$', re.I)

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9\-_\s]", "", s).strip().lower()
    s = re.sub(r"[\s]+", "-", s)
    return s or "post"

def parse_md(path: pathlib.Path):
    text = path.read_text(encoding="utf-8").strip()
    lines = text.splitlines()

    meta = {
        "tag": "Nota",
        "title": path.stem,
        "description": "",
        "datePublished": "1970-01-01",
        "slug": slugify(path.stem),
    }
    body_start = 0

    # Lê cabeçalho simples nas 10 primeiras linhas até linha em branco
    for i, ln in enumerate(lines[:10]):
        m = MD_META_RE.match(ln.strip())
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "slug":
                meta["slug"] = slugify(val)
            else:
                meta[key] = val
        elif not ln.strip():
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()

    # Valida data
    try:
        datetime.strptime(meta["datePublished"], "%Y-%m-%d")
    except Exception:
        meta["datePublished"] = "1970-01-01"

    # Gera excerpt (primeiras ~60 palavras do corpo)
    words = re.findall(r"\S+", body)
    excerpt = " ".join(words[:60]) + ("..." if len(words) > 60 else "")
    meta["excerpt"] = excerpt

    return meta, body

def md_to_html(md: str) -> str:
    md = md.replace("\r\n", "\n")
    def esc(s): return html.escape(s, quote=False)

    # Code blocks ``` ```
    code_blocks = []
    def _codeblock_repl(m):
        lang = m.group(1) or ""
        code = m.group(2)
        code_blocks.append((lang, code))
        return f"§CODEBLOCK{len(code_blocks)-1}§"
    md = re.sub(r"```([\w+-]*)\n(.*?)\n```", _codeblock_repl, md, flags=re.S)

    # Inline code
    md = re.sub(r"`([^`]+)`", lambda m: f"<code>{esc(m.group(1))}</code>", md)

    # **bold** e *italic*
    md = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", md)
    md = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", md)

    # Links [txt](url)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', md)

    # Títulos #, ##, ###
    def heading_repl(m):
        level = min(len(m.group(1)), 3)
        text = m.group(2).strip()
        return f"<h{level}>{text}</h{level}>"
    md = re.sub(r"^(#{1,6})\s+(.*)$", heading_repl, md, flags=re.M)

    # Listas simples -, *
    lines = md.split("\n")
    out = []
    in_ul = False
    for ln in lines:
        if re.match(r"^\s*[-*]\s+", ln):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            item = re.sub(r"^\s*[-*]\s+", "", ln)
            out.append(f"<li>{item}</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(ln)
    if in_ul:
        out.append("</ul>")
    md = "\n".join(out)

    # Parágrafos
    html_lines = []
    for block in re.split(r"\n\s*\n", md.strip()):
        if re.match(r"^\s*<(?:(?:h[1-6])|ul|li|pre|code)", block) or block.startswith("§CODEBLOCK"):
            html_lines.append(block)
        else:
            html_lines.append(f"<p>{block.strip()}</p>")

    html_text = "\n".join(html_lines)

    # Substitui codeblocks
    for i, (lang, code) in enumerate(code_blocks):
        lang_attr = f' data-lang="{html.escape(lang)}"' if lang else ""
        code_html = f'<pre class="code-block"{lang_attr}><code>{esc(code)}</code></pre>'
        html_text = html_text.replace(f"§CODEBLOCK{i}§", code_html)

    return html_text

# IMPORTANTE: todas as chaves { } do CSS foram escapadas para {{ }} e }}}
POST_TEMPLATE_HEAD = """<!doctype html>
<html lang="pt-BR" dir="ltr" itemscope itemtype="https://schema.org/BlogPosting">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>{title} — Pedro Rios</title>
  <meta name="description" content="{description}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title} — Pedro Rios">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:locale" content="pt_BR">
  <meta name="twitter:card" content="summary">
  <link rel="canonical" href="{canonical}">
  <style>
    :root{{--bg:#f6f7f9;--paper:#fff;--text:#1f2833;--muted:#4a5568;--primary:#2f4f79;--border:#d9dde5;--focus:#ffb100;--maxw:74rem}}
    @media(prefers-color-scheme:dark){{:root{{--bg:#0f1720;--paper:#111925;--text:#e8edf4;--muted:#b6c2d1;--primary:#93b9ff;--border:#223047;--focus:#ffd166}}}}
    *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.7 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial}}
    a{{color:var(--primary)}} a:focus-visible{{outline:3px solid var(--focus);outline-offset:3px}}
    header{{border-bottom:1px solid var(--border);background:#ffffffcc;backdrop-filter:saturate(140%) blur(8px);position:sticky;top:0}}
    .container{{max-width:var(--maxw);margin:0 auto;padding:0 1rem}}
    .brand{{display:flex;align-items:center;gap:.75rem;padding:1rem 0}}
    .logo{{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(135deg,#2f4f79,#6a9ea1);color:#fff;font-weight:700}}
    main{{padding:2rem 0}}
    article{{background:var(--paper);border:1px solid var(--border);border-radius:12px;padding:2rem}}
    h1{{margin:0 0 1rem;font-size:clamp(1.7rem,2.2vw + 1rem,2.4rem)}}
    .meta{{color:var(--muted);margin-bottom:1rem}}
    .prose p{{margin:0 0 1rem}}
    .prose ul{{padding-left:1.25rem;margin:0 0 1rem}}
    .code-block{{background:#0b1020;color:#e6edf3;border-radius:8px;padding:1rem;overflow:auto}}
    .back{{display:inline-block;margin-top:1.5rem}}
    footer{{border-top:1px solid var(--border);margin-top:2rem;padding:1rem 0;color:var(--muted)}}
  </style>
</head>
<body>
  <header>
    <div class="container brand">
      <div class="logo" aria-hidden="true">PR</div>
      <div>
        <strong>Pedro Rios</strong><br><span class="meta">Café, estudo e pequenas vitórias diárias.</span>
      </div>
      <nav style="margin-left:auto"><a href="../index.html">Início</a></nav>
    </div>
  </header>
  <main>
    <div class="container">
      <article>
"""

POST_TEMPLATE_TAIL = """
        <a class="back" href="../index.html">← Voltar ao início</a>
      </article>
    </div>
  </main>
  <footer><div class="container"><small>© {year} Pedro Rios • Blog pessoal</small></div></footer>
</body>
</html>
"""

def render_post_html(meta: dict, body_md: str) -> str:
    canonical = f"{BASE_CANONICAL}/posts/{meta['slug']}.html"
    head = POST_TEMPLATE_HEAD.format(
        title=html.escape(meta["title"]),
        description=html.escape(meta.get("description","")),
        canonical=canonical,
    )
    title_block = f'<h1 itemprop="headline">{html.escape(meta["title"])}</h1>\n'
    meta_block = f'<div class="meta" itemprop="datePublished">{meta["datePublished"]}</div>\n'
    body_html = md_to_html(body_md)
    tail = POST_TEMPLATE_TAIL.format(year=datetime.now().year)
    return head + title_block + meta_block + f'<div class="prose" itemprop="articleBody">\n{body_html}\n</div>' + tail

def build():
    if not SRC.exists():
        print("Crie a pasta 'content' e adicione arquivos .md")
        return

    OUT_DIR.mkdir(exist_ok=True)
    posts_index = []

    for md_path in sorted(SRC.glob("*.md")):
        meta, body_md = parse_md(md_path)
        slug = meta["slug"]
        html_out = OUT_DIR / f"{slug}.html"

        # Gera HTML do post
        html_text = render_post_html(meta, body_md)
        html_out.write_text(html_text, encoding="utf-8")

        # Adiciona ao índice
        posts_index.append({
            "tag": meta["tag"],
            "title": meta["title"],
            "description": meta["description"],
            "excerpt": meta["excerpt"],
            "datePublished": meta["datePublished"],
            "url": f"posts/{slug}.html",
        })

    # Ordena índice por data desc
    posts_index.sort(key=lambda x: x.get("datePublished","1970-01-01"), reverse=True)
    OUT_JSON.write_text(json.dumps(posts_index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gerado {OUT_JSON} com {len(posts_index)} posts e HTMLs em {OUT_DIR}/")

if __name__ == "__main__":
    build()
