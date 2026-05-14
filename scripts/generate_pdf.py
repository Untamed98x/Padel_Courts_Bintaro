"""
generate_pdf.py
Convert ExecutiveSummary_PondokLabu.md → styled PDF with active hyperlinks.
Uses playwright (headless Chromium) — links remain clickable in the output PDF.

Usage:
    cd <project-root>
    python scripts/generate_pdf.py

Output:
    output/ExecutiveSummary_PondokLabu.pdf
"""

import re
from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright

ROOT     = Path(__file__).resolve().parents[1]
MD_FILE  = ROOT / 'ExecutiveSummary_PondokLabu.md'
OUT_PDF  = ROOT / 'output' / 'ExecutiveSummary_PondokLabu.pdf'
TMP_HTML = ROOT / 'output' / '_summary_print.html'

VERCEL_URL = 'https://sense-padel-pondoklabu.vercel.app'

# ── 1. Markdown → HTML body ──────────────────────────────────────────────────
md_text = MD_FILE.read_text(encoding='utf-8')

# Strip the plain-text Vercel footer line — the styled callout div replaces it
md_text = re.sub(
    r'\n\*\*Peta interaktif[^\n]+\n?$', '', md_text, flags=re.MULTILINE
)

body_html = markdown.markdown(
    md_text,
    extensions=['tables', 'fenced_code', 'toc', 'nl2br'],
)

# Resolve relative image src to absolute file:// URIs.
# markdown outputs: <img alt="..." src="output/...">  (src not first attribute)
def rewrite_src(m):
    src = m.group(1)
    if src.startswith('http') or src.startswith('data:') or src.startswith('file:'):
        return f'src="{src}"'
    abs_path = (ROOT / src).resolve()
    return f'src="{abs_path.as_uri()}"'

body_html = re.sub(r'src="([^"]+)"', rewrite_src, body_html)

# ── 2. Wrap in print-ready HTML ───────────────────────────────────────────────
full_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sense Padel Pondok Labu — Strategic Snapshot</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}

    body {{
      font-family: 'DM Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
      font-size: 10.5pt;
      line-height: 1.68;
      color: #1a1a2e;
      max-width: 700px;
      margin: 0 auto;
      padding: 28px 36px 48px;
    }}

    h1 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 22pt; font-weight: 700;
      color: #1a1a2e; margin: 0 0 4px;
      line-height: 1.15;
    }}
    h2 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 13pt; font-weight: 700;
      color: #1a1a2e;
      border-bottom: 2px solid #1565C0;
      padding-bottom: 4px;
      margin: 28px 0 12px;
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 10.5pt; font-weight: 700;
      color: #1565C0;
      margin: 18px 0 7px;
      page-break-after: avoid;
    }}

    p {{ margin: 0 0 9px; }}

    blockquote {{
      border-left: 3px solid #1565C0;
      margin: 12px 0;
      padding: 8px 14px;
      background: #f0f8ff;
      border-radius: 0 6px 6px 0;
      color: #333;
      font-size: 10pt;
    }}

    /* Tables */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 9.5pt;
      page-break-inside: avoid;
    }}
    th {{
      background: #1a1a2e;
      color: white;
      padding: 7px 10px;
      text-align: left;
      font-weight: 600;
    }}
    td {{
      padding: 6px 10px;
      border-bottom: 1px solid #e8e8e8;
    }}
    tr:nth-child(even) td {{ background: #f7f9ff; }}

    /* Images */
    img {{
      width: 100%; max-width: 100%;
      border-radius: 8px;
      margin: 12px 0;
      page-break-inside: avoid;
      box-shadow: 0 2px 10px rgba(0,0,0,0.10);
    }}

    /* Links — keep visible and clickable */
    a {{
      color: #1565C0;
      text-decoration: underline;
    }}

    code {{
      background: #f4f4f4;
      padding: 1px 5px; border-radius: 3px;
      font-size: 9pt;
      font-family: 'Courier New', monospace;
    }}

    ul, ol {{ margin: 5px 0 10px 20px; padding: 0; }}
    li {{ margin-bottom: 3px; }}

    hr {{
      border: none;
      border-top: 1px solid #e0e0e0;
      margin: 20px 0;
    }}

    /* Vercel callout at bottom */
    .vercel-callout {{
      background: #1a1a2e;
      color: white;
      border-radius: 8px;
      padding: 11px 16px;
      margin: 28px 0 0;
      font-size: 10pt;
      display: flex; align-items: center; gap: 10px;
      page-break-inside: avoid;
    }}
    .vercel-callout a {{
      color: #69f0ae;
      font-weight: 700;
      text-decoration: none;
    }}

    /* Print settings */
    @media print {{
      body {{ padding: 0; font-size: 10pt; }}
      a {{ color: #1565C0 !important; text-decoration: underline !important; }}
      th {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      tr:nth-child(even) td {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      .vercel-callout {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}
  </style>
</head>
<body>

{body_html}

<div class="vercel-callout">
  <span>
    Peta interaktif (mobile-friendly):
    <a href="{VERCEL_URL}" target="_blank">{VERCEL_URL}</a>
  </span>
</div>

</body>
</html>"""

TMP_HTML.write_text(full_html, encoding='utf-8')
print(f'HTML rendered → {TMP_HTML}')

# ── 3. Playwright: HTML → PDF ─────────────────────────────────────────────────
with sync_playwright() as p:
    browser = p.chromium.launch()
    page    = browser.new_page()
    page.goto(TMP_HTML.as_uri())
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)   # let fonts + images settle

    page.pdf(
        path=str(OUT_PDF),
        format='A4',
        margin={'top': '18mm', 'bottom': '22mm', 'left': '14mm', 'right': '14mm'},
        print_background=True,
        display_header_footer=True,
        header_template='<div></div>',
        footer_template=(
            '<div style="font-size:8px;color:#aaa;width:100%;text-align:center;'
            'font-family:Helvetica,Arial,sans-serif;padding:0 20px">'
            'Sense Padel Pondok Labu — Strategic Snapshot · Mei 2026 &nbsp;·&nbsp; '
            f'<a href="{VERCEL_URL}" style="color:#1565C0">{VERCEL_URL}</a>'
            ' &nbsp;|&nbsp; '
            '<span class="pageNumber"></span>&thinsp;/&thinsp;<span class="totalPages"></span>'
            '</div>'
        ),
    )
    browser.close()

TMP_HTML.unlink(missing_ok=True)

size_kb = OUT_PDF.stat().st_size // 1024
print(f'PDF saved → {OUT_PDF}  ({size_kb} KB)')
print(f'Active link: {VERCEL_URL}')
