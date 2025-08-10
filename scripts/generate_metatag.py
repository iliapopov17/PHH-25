# scripts/generate_metatag.py
from __future__ import annotations
import re
import html
from typing import Optional

_BEGIN = "<!-- BEGIN: AUTO META -->"
_END = "<!-- END: AUTO META -->"


def build_meta(
    *,
    title: str = "Public Health Hackathon'2025 Project",
    description: str = (
        "Exploring patterns in well-being perceptions and healthcare evaluation in Kazakhstan "
        "through interactive geospatial analysis and visualization."
    ),
    url: str = "https://metatags.io/",
    image_url: str = "https://metatags.io/images/meta-tags.png",
) -> str:
    """Return a ready-to-insert HTML meta block (Primary + OpenGraph + Twitter)."""
    # Escape attribute values safely
    esc = html.escape
    title_e = esc(title, quote=True)
    desc_e = esc(description, quote=True)
    url_e = esc(url, quote=True)
    img_e = esc(image_url, quote=True)

    block = f"""\
{_BEGIN}
<!-- Primary Meta Tags -->
<title>{title_e}</title>
<meta name="title" content="{title_e}" />
<meta name="description" content="{desc_e}" />

<!-- Open Graph / Facebook -->
<meta property="og:type" content="website" />
<meta property="og:url" content="{url_e}" />
<meta property="og:title" content="{title_e}" />
<meta property="og:description" content="{desc_e}" />
<meta property="og:image" content="{img_e}" />

<!-- X (Twitter) -->
<meta property="twitter:card" content="summary_large_image" />
<meta property="twitter:url" content="{url_e}" />
<meta property="twitter:title" content="{title_e}" />
<meta property="twitter:description" content="{desc_e}" />
<meta property="twitter:image" content="{img_e}" />

<!-- Meta Tags Generated with https://metatags.io -->
{_END}
"""
    return block


def inject_meta_to_head(html_text: str, meta_block: str) -> str:
    """
    Insert or replace the AUTO META block inside <head>…</head>.
    - If a previous AUTO META block exists, replace it.
    - Otherwise, insert right after the opening <head> tag.
    """
    # Normalize search for <head ...>
    head_open_re = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
    head_close_re = re.compile(r"</head\s*>", re.IGNORECASE)

    # If there is an existing block, replace it
    block_re = re.compile(
        re.escape(_BEGIN) + r".*?" + re.escape(_END),
        flags=re.DOTALL | re.IGNORECASE,
    )
    if block_re.search(html_text):
        return block_re.sub(meta_block, html_text)

    # Otherwise, insert after <head>
    m_open = head_open_re.search(html_text)
    m_close = head_close_re.search(html_text)
    if not (m_open and m_close):
        # No head? Prepend a minimal head.
        return f"<head>\n{meta_block}\n</head>\n" + html_text

    insert_at = m_open.end()
    return html_text[:insert_at] + "\n" + meta_block + "\n" + html_text[insert_at:]


# --- Optional CLI: transform a file in place ---
def _main(path_in: str, path_out: Optional[str] = None, **kwargs):
    with open(path_in, "r", encoding="utf-8") as f:
        html_in = f.read()
    meta = build_meta(**kwargs)
    html_out = inject_meta_to_head(html_in, meta)
    out_path = path_out or path_in
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Meta tags inserted: {out_path}")


if __name__ == "__main__":
    # Minimal CLI usage:
    # python scripts/generate_metatag.py ../docs/index.html
    import sys as _sys

    if len(_sys.argv) < 2:
        print("Usage: python scripts/generate_metatag.py <in.html> [out.html]")
        raise SystemExit(1)
    _main(_sys.argv[1], _sys.argv[2] if len(_sys.argv) > 2 else None)
