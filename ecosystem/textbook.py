"""Per-course textbooks, written by a collaborating author team.

Every course gets six author agents. They are not six voices on the same
question - each owns a different job and reads the previous one's real output:

  LEAD      structures the book and keeps chapters coherent with each other
  EXPERT    writes the substance
  CLINICAL  drags every concept to the bedside - "what does this look like on a
            real patient at 3am"
  ILLUS     specifies the visuals (and captions anything the operator uploads)
  EXAMINER  writes practice items tied to THIS chapter
  EDITOR    checks accuracy, flags uncertainty, cuts padding

Design decisions worth knowing:
  - Chapters are written and stored one at a time. A 12-chapter book in one call
    would be shallow and would blow the timeout.
  - The EDITOR is instructed to flag uncertainty rather than smooth over it.
    This is exam prep for a real nursing licence; a confident wrong sentence is
    worse than an admitted gap.
  - Assets (uploaded images, video, audio) attach to a chapter and are rendered
    inline. The operator uploads; ILLUS captions and places them.
  - Nothing here runs on a schedule. Authoring is always operator-initiated.
"""
import html as _html
import json, os, re, shutil, sqlite3, threading, time

import llm, loops

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
ASSETS = os.path.join(HERE, "assets")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS tb_books(
  course TEXT PRIMARY KEY, title TEXT, outline TEXT, status TEXT,
  created INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS tb_chapters(
  course TEXT, n INTEGER, title TEXT, summary TEXT, body TEXT,
  visuals TEXT, items TEXT, notes TEXT, status TEXT, words INTEGER,
  created INTEGER, updated INTEGER, PRIMARY KEY(course, n));
CREATE TABLE IF NOT EXISTS tb_assets(
  id INTEGER PRIMARY KEY AUTOINCREMENT, course TEXT, chapter INTEGER,
  kind TEXT, filename TEXT, caption TEXT, alt TEXT, source TEXT, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_tb_assets ON tb_assets(course, chapter);
"""

# The author team. Same six roles on every course; the mandate text is what
# differs once the course subject is folded in.
TEAM = [
    ("LEAD",     "Lead Author",        "structure and coherence"),
    ("EXPERT",   "Subject Expert",     "the substance"),
    ("CLINICAL", "Clinical Correlator", "bedside application"),
    ("ILLUS",    "Illustrator",        "visuals and captions"),
    ("EXAMINER", "Examiner",           "practice items"),
    ("EDITOR",   "Editor",             "accuracy and cuts"),
]

# Applied to every single call in this module. Non-negotiable.
GUARD = (
    "This is study material for a nursing student preparing for the NCLEX. "
    "Accuracy matters more than fluency: if you are not confident about a "
    "clinical specific - a dose, a lab value, a protocol - say so explicitly "
    "rather than stating it. Never invent a citation. This is exam preparation, "
    "not clinical guidance for treating a real patient."
)


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    os.makedirs(ASSETS, exist_ok=True)
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


def _course(code):
    import nursing_api
    return nursing_api.COURSES.get(code)


def _agent(code, role):
    return f"TB-{code}-{role}"


# ─────────────────────────────────────────────────────────── outline
def outline(code, chapters=8):
    """LEAD lays out the book. Grounded in the course's own lesson content."""
    co = _course(code)
    if not co:
        return None, f"unknown course {code!r}"
    terms = ", ".join(t[0] for t in (co.get("terms") or [])[:12])
    system = (
        f"You are the Lead Author for a nursing textbook covering {co['name']} "
        f"({code}), a {co['credits']}-credit {co.get('type','')} course in an "
        f"accelerated BSN program.\n{GUARD}\n\n"
        f"Course focus: {co.get('blurb','')}\n"
        f"Core lesson: {(co.get('lesson') or '')[:1200]}\n"
        f"Key terms it must cover: {terms}\n\n"
        f"Produce exactly {chapters} chapters that build on each other, moving from "
        "foundation to application. Every key term above must land in some chapter."
    )
    want = ('A JSON array of chapter objects: '
            '[{"n":1,"title":"...","summary":"one sentence","covers":["term","term"]}]')
    data, err = llm.ask_json(system + "\n\n" + want,
                             f"Outline the {chapters} chapters.", want="array", timeout=240)
    if err:
        return None, err
    chs = []
    for i, ch in enumerate(data, 1):
        if not isinstance(ch, dict):
            continue
        chs.append({"n": i, "title": str(ch.get("title", f"Chapter {i}"))[:120],
                    "summary": str(ch.get("summary", ""))[:400],
                    "covers": [str(x)[:60] for x in (ch.get("covers") or [])][:8]})
    if not chs:
        return None, "no chapters parsed"
    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("""INSERT INTO tb_books(course,title,outline,status,created,updated)
                     VALUES(?,?,?,?,?,?) ON CONFLICT(course) DO UPDATE SET
                     title=?,outline=?,status=?,updated=?""",
                  (code, co["name"], json.dumps(chs), "outlined", now, now,
                   co["name"], json.dumps(chs), "outlined", now))
        for ch in chs:
            c.execute("""INSERT OR IGNORE INTO tb_chapters
                         (course,n,title,summary,status,created,updated)
                         VALUES(?,?,?,?,?,?,?)""",
                      (code, ch["n"], ch["title"], ch["summary"], "planned", now, now))
    return {"course": code, "title": co["name"], "chapters": chs}, None


def get_outline(code):
    with LOCK, _c() as c:
        b = c.execute("SELECT * FROM tb_books WHERE course=?", (code,)).fetchone()
        chs = [dict(r) for r in c.execute(
            "SELECT n,title,summary,status,words FROM tb_chapters WHERE course=? ORDER BY n",
            (code,))]
    if not b:
        return None
    return {"course": code, "title": b["title"], "status": b["status"], "chapters": chs}


# The task goes in the USER turn. Appended system text gets diluted: an Editor
# briefed only in the system prompt replied with a chatty menu of study options
# instead of a review. Stated as the user's actual request, it reviews.
STAGE_SPECS = {
    "EXPERT": ("EXPERT", "You are the Subject Expert on this textbook's author team.",
        "Write the body of this chapter: 700-1200 words of clear teaching prose. "
        "Explain mechanisms, not just facts - the student must understand WHY so they "
        "can reason through a question they have never seen. Bold key terms with "
        "**term**. Write the chapter and nothing else: no preamble, no closing offer "
        "of further help."),
    "CLINICAL": ("CLINICAL", "You are the Clinical Correlator on this textbook's author team.",
        "Below is the chapter draft. Write the section that puts it at the bedside: "
        "what this looks like on a real patient, the assessment findings that matter, "
        "the mistake students reliably make, and the one finding that would make you "
        "escalate. 250-400 words. Output only that section - no preamble, no sign-off."),
    "ILLUS": ("ILLUS", "You are the Illustrator on this textbook's author team.",
        "Below is the chapter. Specify the 2-4 visuals that would genuinely aid "
        "understanding - a comparison table, a concept map, a labelled diagram, a flow "
        "chart. For each give a title, what it shows, and enough detail to draw it. "
        "Where a table is the right answer, write the actual table in markdown so it "
        "renders directly. Output only the visuals."),
    "REDTEAM": ("REDTEAM", "You are the Red Team on this textbook's author team. Your job "
                "is to attack the draft, not to be fair to it.",
        "Below is the draft. Find the three weakest claims in it - the ones a sharp "
        "examiner would puncture. For each: quote it, say precisely why it is weak, and "
        "state what would have to be true for it to hold. Do not praise anything and do "
        "not rewrite it."),
    "EDITOR": ("EDITOR", "You are the Editor on this textbook's author team. You are the last "
               "check before a nursing student studies from this material.",
        "Below is the assembled chapter. Review it. List: (1) any statement you believe "
        "is clinically inaccurate or dangerously oversimplified, (2) anything asserted "
        "with more confidence than the evidence supports, (3) anything that should be "
        "cut as padding. Quote the specific text in each case. If a section is sound, "
        "say so in one line. Do not rewrite the chapter, do not summarise it, and do "
        "not offer to help further - return the review only."),
}


def _pick_loop(force=None):
    try:
        loops.init()
        return loops.choose("chapter", force)
    except Exception:
        return "classic", "loops unavailable"


# ─────────────────────────────────────────────────────── write a chapter
def write_chapter(code, n, force_loop=None):
    """The full author chain for one chapter. Each stage reads the last.

    Which chain runs is chosen by `loops` — mostly the best-scoring one so far,
    sometimes a different one so the comparison keeps improving. The result is
    scored on measurable properties and remembered.
    """
    co = _course(code)
    if not co:
        return None, f"unknown course {code!r}"
    with LOCK, _c() as c:
        row = c.execute("SELECT * FROM tb_chapters WHERE course=? AND n=?",
                        (code, n)).fetchone()
        book = c.execute("SELECT outline FROM tb_books WHERE course=?", (code,)).fetchone()
    if not row:
        return None, f"chapter {n} not outlined yet"
    plan = {}
    for ch in json.loads(book["outline"]) if book else []:
        if ch.get("n") == n:
            plan = ch
    covers = ", ".join(plan.get("covers") or [])
    head = (f"Course: {co['name']} ({code}). Chapter {n}: {row['title']}.\n"
            f"Chapter should cover: {covers or row['summary']}\n"
            f"Course lesson context: {(co.get('lesson') or '')[:900]}")

    loop, why = _pick_loop(force_loop)
    spec = loops.catalogue("chapter").get(loop) or loops.CHAPTER_LOOPS["classic"]
    stages = [STAGE_SPECS[r] for r in spec["stages"] if r in STAGE_SPECS]

    out, carry, t0 = {}, "", time.time()
    for role, who, task in stages:
        # Context AND task both go in the user turn. Leaving the chapter brief in
        # the system prompt produced a 138-word chapter and two downstream agents
        # replying "no chapter text was included" — they never saw it.
        system = f"{who}\n\n{GUARD}"
        user = f"CHAPTER BRIEF\n{head}\n\n"
        if carry:
            user += f"{carry}\n\n"
        user += f"---\n\nYOUR TASK\n{task}"
        text, err = llm.ask(system, user, timeout=300)
        if err:
            return None, f"{role}: {err}"
        out[role] = text
        # Accumulate — do not replace. Overwriting here meant the Editor received
        # only the Illustrator's visual specs and replied "no chapter text was
        # included". Each stage must see everything written before it.
        parts = [f"[chapter body]\n{out['EXPERT']}"]
        for key, label in (("CLINICAL", "bedside section"),
                           ("ILLUS", "visual specifications"),
                           ("REDTEAM", "red team's objections")):
            if out.get(key):
                parts.append(f"[{label}]\n{out[key]}")
        carry = "\n\n".join(parts)

    # Loops vary which stages run, so nothing downstream may assume a stage fired.
    body = out["EXPERT"]
    if out.get("CLINICAL"):
        body += "\n\n## At the bedside\n\n" + out["CLINICAL"]
    if out.get("REDTEAM"):
        body += "\n\n## Where this gets challenged\n\n" + out["REDTEAM"]
    words = len(body.split())

    # EXAMINER writes items against the finished chapter, via the existing pipeline
    items = []
    try:
        import nursing_api
        qs, qerr = nursing_api.generate_questions(
            code, n=3, focus=f"{row['title']} — {covers or row['summary']}")
        if not qerr:
            items = [q.get("id") for q in (qs or [])]
    except Exception:
        pass

    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("""UPDATE tb_chapters SET body=?,visuals=?,notes=?,items=?,status=?,
                     words=?,updated=? WHERE course=? AND n=?""",
                  (body, out.get("ILLUS", ""), out.get("EDITOR", ""), json.dumps(items),
                   "drafted", words, now, code, n))

    # Score what this loop actually produced, and remember it.
    secs = round(time.time() - t0, 1)
    score, metrics = 0, {}
    try:
        score, metrics = loops.score_chapter(
            {"body": body, "notes": out.get("EDITOR", ""), "visuals": out.get("ILLUS", "")},
            items=len(items))
        loops.record("chapter", loop, f"{code}-ch{n}", score, metrics, secs)
    except Exception:
        pass
    return {"course": code, "n": n, "title": row["title"], "words": words,
            "items": len(items), "seconds": secs,
            "loop": loop, "loop_reason": why, "score": score, "metrics": metrics,
            "editor_notes": out.get("EDITOR", "")[:600]}, None


def get_chapter(code, n):
    with LOCK, _c() as c:
        r = c.execute("SELECT * FROM tb_chapters WHERE course=? AND n=?", (code, n)).fetchone()
        assets = [dict(a) for a in c.execute(
            "SELECT * FROM tb_assets WHERE course=? AND chapter=? ORDER BY id", (code, n))]
    if not r:
        return None
    d = dict(r)
    d["assets"] = assets
    return d


# ───────────────────────────────────────────────────────────── assets
KINDS = {".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
         ".webp": "image", ".svg": "image", ".mp4": "video", ".webm": "video",
         ".mov": "video", ".mp3": "audio", ".wav": "audio", ".m4a": "audio"}


def add_asset(code, chapter, path, caption="", source="upload"):
    """Attach an uploaded file to a chapter. Copies it into assets/."""
    if not os.path.exists(path):
        return None, f"no such file: {path}"
    ext = os.path.splitext(path)[1].lower()
    kind = KINDS.get(ext)
    if not kind:
        return None, f"unsupported type {ext}"
    os.makedirs(ASSETS, exist_ok=True)
    safe = f"{code}_ch{chapter}_{int(time.time())}{ext}"
    shutil.copy2(path, os.path.join(ASSETS, safe))
    with LOCK, _c() as c:
        c.execute("""INSERT INTO tb_assets(course,chapter,kind,filename,caption,alt,source,created)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (code, chapter, kind, safe, caption[:400], caption[:200], source,
                   int(time.time())))
    return {"filename": safe, "kind": kind, "caption": caption}, None


def caption_asset(code, chapter, filename, what_it_shows):
    """ILLUS writes a teaching caption for something the operator uploaded."""
    co = _course(code)
    ch = get_chapter(code, chapter) or {}
    system = (f"You are the Illustrator for {co['name'] if co else code}, chapter "
              f"{chapter}: {ch.get('title','')}.\n{GUARD}\n\n"
              "The operator uploaded a figure. Write a caption that TEACHES - one or "
              "two sentences naming what the student should notice and why it matters "
              "for the exam. Then a second line beginning 'ALT: ' describing the image "
              "for a screen reader. Nothing else.")
    text, err = llm.ask(system, f"The figure shows: {what_it_shows}\n\n"
                                f"Chapter context: {(ch.get('body') or '')[:800]}")
    if err:
        return None, err
    cap = text.split("ALT:")[0].strip()
    alt = text.split("ALT:")[1].strip() if "ALT:" in text else what_it_shows
    with LOCK, _c() as c:
        c.execute("UPDATE tb_assets SET caption=?, alt=? WHERE course=? AND chapter=? AND filename=?",
                  (cap[:400], alt[:200], code, chapter, filename))
    return {"caption": cap, "alt": alt}, None


# ───────────────────────────────────────────────────────────── render
def _md(t):
    """Just enough markdown for what the authors actually emit."""
    t = _html.escape(t or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"^## (.+)$", r"<h3>\1</h3>", t, flags=re.M)
    out, table = [], []
    for para in re.split(r"\n\s*\n", t):
        p = para.strip()
        if not p:
            continue
        if p.startswith("<h3>"):
            out.append(p); continue
        if "|" in p and p.count("\n") >= 1:                 # a markdown table
            rows = [r for r in p.splitlines() if r.strip().startswith("|")]
            if len(rows) >= 2:
                cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows
                         if not re.match(r"^\|[\s:\-|]+\|$", r.strip())]
                if cells:
                    head = "".join(f"<th>{c}</th>" for c in cells[0])
                    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                                   for r in cells[1:])
                    out.append(f"<table><tr>{head}</tr>{body}</table>")
                    continue
        out.append("<p>" + p.replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def render(code):
    """Assemble the whole book into one standalone HTML page."""
    ol = get_outline(code)
    if not ol:
        return None, "not outlined yet"
    parts = []
    for meta in ol["chapters"]:
        ch = get_chapter(code, meta["n"]) or {}
        if not ch.get("body"):
            parts.append(f'<section><h2>{meta["n"]}. {_html.escape(meta["title"])}</h2>'
                         f'<p class="todo">Not written yet.</p></section>')
            continue
        media = ""
        for a in ch.get("assets", []):
            src = "assets/" + a["filename"]
            if a["kind"] == "image":
                tag = f'<img src="{src}" alt="{_html.escape(a["alt"] or "")}">'
            elif a["kind"] == "video":
                tag = f'<video src="{src}" controls></video>'
            else:
                tag = f'<audio src="{src}" controls></audio>'
            media += f'<figure>{tag}<figcaption>{_html.escape(a["caption"] or "")}</figcaption></figure>'
        parts.append(
            f'<section><h2>{meta["n"]}. {_html.escape(meta["title"])}</h2>'
            f'<p class="sum">{_html.escape(meta["summary"] or "")}</p>'
            f'{_md(ch["body"])}{media}'
            + (f'<div class="vis"><h3>Visuals</h3>{_md(ch.get("visuals") or "")}</div>'
               if ch.get("visuals") else "")
            + (f'<details class="ed"><summary>Editor notes</summary>{_md(ch.get("notes") or "")}</details>'
               if ch.get("notes") else "")
            + '</section>')

    doc = f"""<!doctype html><meta charset=utf-8><title>{_html.escape(ol['title'])}</title>
<style>
:root{{--bg:#0b0a14;--card:#15131f;--line:#2b2743;--ink:#e9e6f5;--dim:#9089ab;--v:#8b7cf6}}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--bg);color:var(--ink);font:16px/1.75 Georgia,serif;padding:32px 20px 80px}}
.wrap{{max-width:760px;margin:0 auto}}
h1{{font:500 30px/1.2 system-ui;letter-spacing:.01em}}
.meta{{color:var(--dim);font:13px/1.6 system-ui;margin-top:6px}}
h2{{font:500 22px/1.3 system-ui;margin:38px 0 4px;color:#fff}}
h3{{font:500 15px/1.4 system-ui;color:var(--v);margin:22px 0 6px;letter-spacing:.02em}}
.sum{{color:var(--dim);font:italic 15px/1.6 Georgia,serif;margin-bottom:14px}}
p{{margin:0 0 14px}} strong{{color:#fff;font-weight:600}}
table{{width:100%;border-collapse:collapse;font:14px/1.5 system-ui;margin:14px 0}}
th,td{{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}}
th{{background:var(--card);color:var(--v);font-weight:500}}
figure{{margin:18px 0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}
figure img,figure video{{width:100%;border-radius:6px;display:block}}
figcaption{{color:var(--dim);font:13px/1.6 system-ui;margin-top:8px}}
.vis{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:18px 0}}
.ed{{margin:14px 0;color:var(--dim);font:14px/1.6 system-ui}}
.ed summary{{cursor:pointer;color:var(--v)}}
.todo{{color:var(--dim);font-style:italic}}
section{{border-top:1px solid var(--line);padding-top:8px}}
</style>
<div class=wrap>
<h1>{_html.escape(ol['title'])}</h1>
<div class=meta>{_html.escape(code)} · {len(ol['chapters'])} chapters · written by the course author team</div>
{''.join(parts)}
</div>"""
    path = os.path.join(HERE, f"textbook_{code}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return {"path": path, "chapters": len(ol["chapters"]),
            "written": sum(1 for c in ol["chapters"] if c["status"] == "drafted")}, None


def status():
    with LOCK, _c() as c:
        books = [dict(r) for r in c.execute(
            """SELECT b.course, b.title, b.status,
                      (SELECT COUNT(*) FROM tb_chapters t WHERE t.course=b.course) total,
                      (SELECT COUNT(*) FROM tb_chapters t WHERE t.course=b.course
                       AND t.status='drafted') done,
                      (SELECT COALESCE(SUM(words),0) FROM tb_chapters t WHERE t.course=b.course) words
               FROM tb_books b ORDER BY b.course""")]
    return books


if __name__ == "__main__":
    init()
    print("author team per course:", ", ".join(r[1] for r in TEAM))
    print("books so far:", status() or "none")
