"""Dump docx paragraph text to UTF-8 file for inspection."""
from pathlib import Path

import docx

ROOT = Path(__file__).resolve().parents[1]
doc_path = ROOT / "MathorCup_2026_paper_working.docx"
out_path = ROOT / "_template_dump_utf8.txt"

d = docx.Document(str(doc_path))
lines: list[str] = []
for i, p in enumerate(d.paragraphs):
    t = p.text
    if not t.strip():
        continue
    st = p.style.name if p.style else ""
    lines.append(f"--- para {i} style={st} ---\n{t}\n")

out_path.write_text("".join(lines), encoding="utf-8")
print("wrote", out_path, "blocks", len(lines))
