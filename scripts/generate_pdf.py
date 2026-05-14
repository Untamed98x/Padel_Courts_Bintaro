"""
Convert EXECUTIVE_SUMMARY.md → styled HTML → PDF via Chrome headless
"""
import base64
import os
import re
import subprocess
import sys
import tempfile
import markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MD_FILE  = os.path.join(BASE_DIR, 'EXECUTIVE_SUMMARY.md')
OUT_PDF  = os.path.join(BASE_DIR, 'Executive_Summary_SurfingWhale.pdf')
CHROME   = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

def embed_images(md_text):
    """Replace ![alt](src/file.png) with base64 data URIs."""
    def replace(m):
        alt  = m.group(1)
        path = m.group(2)
        # decode percent-encoded spaces
        path_decoded = path.replace('%20', ' ').replace('%26', '&')
        full = os.path.join(BASE_DIR, path_decoded)
        if not os.path.exists(full):
            return m.group(0)
        with open(full, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        return f'![{alt}](data:image/png;base64,{data})'
    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace, md_text)

def md_to_html(md_text):
    body = markdown.markdown(
        md_text,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #1a1a2e;
    background: #fff;
    padding: 0;
  }}

  /* Cover strip */
  .cover {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    color: white;
    padding: 48px 56px 40px;
    margin-bottom: 36px;
  }}
  .cover h1 {{
    font-size: 26pt;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
    color: #fff;
    border: none;
  }}
  .cover h2 {{
    font-size: 13pt;
    font-weight: 400;
    color: #a8c6fa;
    margin-bottom: 20px;
    border: none;
    padding: 0;
  }}
  .cover p {{
    font-size: 9.5pt;
    color: #c8d8f0;
    line-height: 1.8;
    margin: 0;
  }}
  .cover strong {{ color: #fff; }}

  /* Main content wrapper */
  .content {{
    padding: 0 56px 56px;
  }}

  h1 {{ display: none; }}  /* hidden — shown in cover */
  h2 {{
    font-size: 14pt;
    font-weight: 700;
    color: #0f3460;
    border-bottom: 2px solid #0f3460;
    padding-bottom: 5px;
    margin: 32px 0 14px;
  }}
  h3 {{
    font-size: 11pt;
    font-weight: 600;
    color: #16213e;
    margin: 22px 0 8px;
  }}

  p {{ margin: 8px 0; }}

  ul, ol {{
    padding-left: 20px;
    margin: 8px 0 12px;
  }}
  li {{ margin-bottom: 4px; }}

  blockquote {{
    border-left: 4px solid #0f3460;
    background: #eef4ff;
    padding: 10px 16px;
    margin: 14px 0;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #16213e;
  }}

  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
    font-size: 9.5pt;
  }}
  th {{
    background: #0f3460;
    color: #fff;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
  }}
  td {{
    padding: 7px 12px;
    border-bottom: 1px solid #e2e8f0;
  }}
  tr:nth-child(even) td {{ background: #f7faff; }}

  img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 16px auto;
    border-radius: 6px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10);
  }}

  code {{
    background: #f0f4f8;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 9pt;
  }}

  strong {{ font-weight: 600; }}

  hr {{
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 28px 0;
  }}

  .footer {{
    margin-top: 40px;
    padding-top: 14px;
    border-top: 1px solid #e2e8f0;
    font-size: 8.5pt;
    color: #888;
    text-align: center;
  }}

  @media print {{
    body {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
    .cover {{ -webkit-print-color-adjust: exact; }}
    h2 {{ page-break-before: auto; }}
    img {{ page-break-inside: avoid; }}
    table {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<div class="cover">
  <h1>Executive Summary</h1>
  <h2>Riset Pasar Aplikasi Finance — Validasi Segmen Pengguna</h2>
  <p>
    <strong>Prepared for:</strong> Surfing Whale Finance &nbsp;|&nbsp;
    <strong>Periode data:</strong> Maret–April 2026<br>
    <strong>Market:</strong> Indonesia (ID) &amp; United States (US) &nbsp;|&nbsp;
    <strong>Total review:</strong> 1.050 (600 ID + 450 US)
  </p>
</div>
<div class="content">
{body}
<div class="footer">Surfing Whale Finance — Internal Research Document · April 2026</div>
</div>
</body>
</html>"""

def main():
    with open(MD_FILE, encoding='utf-8') as f:
        raw = f.read()

    # strip first two heading lines (shown in cover div already)
    lines = raw.split('\n')
    clean = '\n'.join(l for l in lines if not l.startswith('# ') and not (l.startswith('## ') and 'Riset Pasar' in l))

    print('Embedding images...')
    embedded = embed_images(clean)

    print('Converting markdown → HTML...')
    html = md_to_html(embedded)

    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as tf:
        tf.write(html)
        tmp_html = tf.name

    print(f'Launching Chrome headless → {OUT_PDF}')
    result = subprocess.run([
        CHROME,
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        f'--print-to-pdf={OUT_PDF}',
        '--print-to-pdf-no-header',
        '--no-pdf-header-footer',
        f'file://{tmp_html}'
    ], capture_output=True, text=True, timeout=60)

    os.unlink(tmp_html)

    if result.returncode != 0:
        print('Chrome stderr:', result.stderr[:500])
        sys.exit(1)

    size_kb = os.path.getsize(OUT_PDF) / 1024
    print(f'Done → {OUT_PDF} ({size_kb:.0f} KB)')

if __name__ == '__main__':
    main()
