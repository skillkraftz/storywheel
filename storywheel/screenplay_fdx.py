"""A screenplay as a Final Draft file (.fdx: Final Draft's XML), for anyone who wants the script in Final Draft, Fade In or WriterDuet.

    write(text, path, title_page) -> path

Each Fountain element becomes a Paragraph of the matching type (Scene Heading, Action, Character, Parenthetical, Dialogue, Transition;
centered text is a centered Action, lyrics are Lyrics). Two speeches side by side sit in a DualDialogue. *Italic*, **bold** and _underline_
become Text styles. Sections and synopses are not printed, so they are left out; a page break (===) starts the next paragraph on a new page."""
from pathlib import Path
from xml.sax.saxutils import escape

from . import fountain
from .screenplay_pdf import runs_of

TYPES = {"heading": "Scene Heading", "action": "Action", "character": "Character", "parenthetical": "Parenthetical",
         "dialogue": "Dialogue", "transition": "Transition", "centered": "Action", "lyrics": "Lyrics"}


def _texts(text):
    out = []
    for r in runs_of(text.replace("\n", " ")):
        styles = [s for s, on in (("Bold", r.bold), ("Italic", r.italic), ("Underline", r.underline)) if on]
        attr = f' Style="{"+".join(styles)}"' if styles else ""
        out.append(f"<Text{attr}>{escape(r.text)}</Text>")
    return "".join(out) or "<Text></Text>"


def _paragraph(kind, text, extra=""):
    return f'    <Paragraph Type="{kind}"{extra}>\n      {_texts(text)}\n    </Paragraph>'


def write(text, path, title_page=None):
    script = fountain.parse(text)
    paras = []
    els = [e for e in script.elements if e.type not in ("section", "synopsis")]
    page_break = False
    i = 0
    while i < len(els):
        e = els[i]
        extra = ' StartsNewPage="Yes"' if page_break else ""
        page_break = False
        if e.type == "page_break":
            page_break = True
            i += 1
            continue
        if e.type == "character":
            j = i + 1
            while j < len(els) and els[j].type in ("parenthetical", "dialogue"):
                j += 1
            block = [_paragraph("Character", e.name + (" " + e.ext if e.ext else ""), extra)]
            block += [_paragraph(TYPES[x.type], x.text) for x in els[i + 1:j]]
            if j < len(els) and els[j].type == "character" and els[j].dual and not e.dual:
                k = j + 1
                while k < len(els) and els[k].type in ("parenthetical", "dialogue"):
                    k += 1
                other = [_paragraph("Character", els[j].name + (" " + els[j].ext if els[j].ext else ""))]
                other += [_paragraph(TYPES[x.type], x.text) for x in els[j + 1:k]]
                paras.append("    <DualDialogue>\n" + "\n".join(block + other) + "\n    </DualDialogue>")
                i = k
            else:
                paras += block
                i = j
            continue
        if e.type in ("heading", "transition"):
            paras.append(_paragraph(TYPES[e.type], e.text.upper(), extra))
        elif e.type == "centered":
            paras.append(_paragraph("Action", e.text, extra + ' Alignment="Center"'))
        else:
            paras.append(_paragraph(TYPES.get(e.type, "Action"), e.text, extra))
        i += 1
    tp = title_page or {}
    title_paras = []
    for line in tp.get("title") or []:
        title_paras.append(f'    <Paragraph Alignment="Center"><Text>{escape(line)}</Text></Paragraph>')
    if tp.get("credit"):
        title_paras.append('    <Paragraph Alignment="Center"><Text></Text></Paragraph>')
        title_paras.append(f'    <Paragraph Alignment="Center"><Text>{escape(tp["credit"])}</Text></Paragraph>')
    for a in tp.get("author") or []:
        title_paras.append(f'    <Paragraph Alignment="Center"><Text>{escape(a)}</Text></Paragraph>')
    for c in tp.get("contact") or []:
        title_paras.append(f'    <Paragraph Alignment="Left"><Text>{escape(c)}</Text></Paragraph>')
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
           '<FinalDraft DocumentType="Script" Template="No" Version="5">\n'
           '  <Content>\n' + "\n".join(paras) + '\n  </Content>\n'
           '  <TitlePage>\n    <Content>\n' + "\n".join(title_paras) + '\n    </Content>\n  </TitlePage>\n'
           '</FinalDraft>\n')
    path = Path(path)
    path.write_text(xml, encoding="utf-8")
    return path
