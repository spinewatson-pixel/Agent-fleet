"""The Intake - uploads in, verified institutional knowledge out.

This is deliberately separate from the courses. You drop in an image, a slide,
a handout, a photographed page; a chain of agents turns it into knowledge cards
that every other agent in the nursing stack can read. The courses consume the
library; they don't own it.

The chain, and why each link exists:

  CURATOR    identifies what the artefact actually is and which course(s) it
             serves. Filing is a separate job from reading - an agent asked to
             do both does neither well.
  EXTRACTOR  pulls the content out. For images this is the expensive, careful
             pass: every label, axis, arrow, value and relationship, because a
             half-read diagram is worse than no diagram.
  VERIFIER   a SECOND agent that never saw the extraction being made, checking
             each claim independently against what it knows. This is the whole
             difference between "an agent said so" and institutional grade. It
             can mark a claim verified, corrected, or disputed - and disputed
             claims stay in the library flagged, not silently deleted.
  LIBRARIAN  files the surviving claims as atomic cards against course and topic
             so they are retrievable by the agents that need them.

What makes it compound: `brief()` pulls the relevant verified cards into any
other agent's prompt. A diagram you upload today shows up inside a tutor's
answer next week, cited to the source you gave it. That is the "agents learning
from each other" part - not agents chatting, agents sharing a checked store.

Nothing here runs on a schedule. You submit; the chain runs once.
"""
import hashlib, json, os, re, shutil, sqlite3, threading, time

import llm

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LIB = os.path.join(HERE, "library")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS kb_source(
  id TEXT PRIMARY KEY, filename TEXT, kind TEXT, title TEXT, summary TEXT,
  courses TEXT, discipline TEXT, topics TEXT, note TEXT, status TEXT,
  cards INTEGER DEFAULT 0, created INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS kb_card(
  id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT, course TEXT, topic TEXT,
  kind TEXT, claim TEXT, detail TEXT, confidence REAL, verdict TEXT,
  verifier_note TEXT, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_kb_card ON kb_card(course, topic);
CREATE INDEX IF NOT EXISTS ix_kb_card_src ON kb_card(source_id);
"""

IMG = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
DOC = (".pdf", ".txt", ".md", ".csv", ".html", ".docx")
CARD_KINDS = ("fact", "mechanism", "value", "procedure", "visual", "comparison", "mnemonic")

GUARD = ("This is study material for a nursing student preparing for the NCLEX. "
         "Precision matters more than completeness: never state a lab value, dose or "
         "protocol you are not confident of - mark it uncertain instead. This is exam "
         "preparation, not clinical guidance for a real patient.")


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    os.makedirs(LIB, exist_ok=True)
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


def _kind(path):
    e = os.path.splitext(path)[1].lower()
    return "image" if e in IMG else ("doc" if e in DOC else "")


def _catalogue():
    import nursing_api
    return "\n".join(f"  {k} - {v['name']} (term {v.get('term')})"
                     for k, v in sorted(nursing_api.COURSES.items()))


# ───────────────────────────────────────────────────────────── the chain
def _curate(path, kind, hint):
    """CURATOR: what is this, and where does it belong."""
    system = (
        "You are the Curator for a nursing student's knowledge library.\n" + GUARD + "\n\n"
        "COURSES IN THE PROGRAM:\n" + _catalogue() + "\n\n"
        + ("The artefact is an image. Use the Read tool on the path given to look at it.\n"
           if kind == "image" else
           "The artefact is a document. Use the Read tool on the path given to read it.\n")
        + "Identify it and file it. Assign it to every course it genuinely serves - "
        "usually one or two; do not scatter it across the catalogue.\n\n"
        "Describe what it is, what it contains, and which courses it serves.")
    user = f"File path: {path}\n" + (f"Operator note: {hint}" if hint else "")
    shape = ('A single JSON object: {"title":"short descriptive title","kind":"diagram|'
             'table|slide|notes|photo|handout|chart|text","summary":"two sentences on '
             'what it contains","courses":["A300"],"discipline":"the underlying science",'
             '"topics":["specific topic","specific topic"]}\n\nValid course codes:\n'
             + _catalogue())
    data, err, _seen = llm.read_then_json(system, user, shape, want="object", timeout=300)
    return data, err


def _extract(path, kind, meta):
    """EXTRACTOR: read it properly. Visuals get the careful pass."""
    visual = (
        "This is a visual. Read it exhaustively - that is the job. Every label, every "
        "axis and its units, every arrow and what it connects, every number, every "
        "colour that carries meaning, the direction of each relationship, and anything "
        "the figure implies but does not print. If part of it is illegible, say which "
        "part rather than guessing.\n\n"
        if kind == "image" else
        "Read the document fully and pull out what is actually teachable. Skip "
        "administrative furniture - due dates, page numbers, headers.\n\n")
    system = (
        f"You are the Extractor for a nursing knowledge library.\n{GUARD}\n\n"
        f"ARTEFACT: {meta.get('title','')} — {meta.get('summary','')}\n"
        f"Serves: {', '.join(meta.get('courses') or [])}\n\n"
        "Use the Read tool on the path given.\n\n" + visual +
        "Break the content into atomic claims - one idea each, standalone, so it still "
        "makes sense pulled out of context months from now. Quantities keep their units. "
        "Mechanisms state cause and effect. Do not add knowledge that is not in the "
        "artefact; the point is to capture THIS source faithfully. Number them.")
    shape = ('A JSON array: [{"kind":"fact|mechanism|value|procedure|visual|comparison|'
             'mnemonic","topic":"specific topic","claim":"one precise sentence",'
             '"detail":"the supporting explanation, values, or spatial description",'
             '"confidence":0.0-1.0}]\n\nOne entry per claim in the description. Keep '
             'every one — do not summarise the list down.')
    data, err, _seen = llm.read_then_json(system, f"File path: {path}", shape,
                                          want="array", timeout=420)
    return data, err


def _verify(cards, meta):
    """VERIFIER: an independent second agent. Never saw the extraction happen."""
    listing = "\n".join(
        f"{i}. [{c.get('kind')}] {c.get('claim')}\n   detail: {str(c.get('detail',''))[:300]}"
        for i, c in enumerate(cards))
    system = (
        "You are the Verifier for a nursing knowledge library. Another agent extracted "
        "the claims below from a source artefact. You did not see that process. Your job "
        "is to check each claim against established nursing and biomedical science before "
        "it enters the library.\n" + GUARD + "\n\n"
        f"SOURCE CONTEXT: {meta.get('title','')} — {meta.get('summary','')}\n\n"
        "For each claim return a verdict:\n"
        "  verified  - accurate as written\n"
        "  corrected - substantially right but the wording or a value needs fixing; "
        "supply the corrected claim\n"
        "  disputed  - you believe it is wrong or dangerously oversimplified; say why\n"
        "  unclear   - cannot be judged without seeing the source\n\n"
        "Be a real check, not a rubber stamp - but do not manufacture disagreement "
        "either. A claim that is simply correct gets 'verified' and a one-line note.")
    # Schema in the user turn — see llm.read_then_json for why.
    user = (
        "CLAIMS TO CHECK:\n" + listing[:13000] + "\n\n"
        "Return one entry per claim above, using its number as \"i\".\n"
        'FORMAT: [{"i":0,"verdict":"verified|corrected|disputed|unclear",'
        '"note":"one sentence","corrected_claim":"only when verdict is corrected"}]')
    return llm.ask_json(system, user, want="array", timeout=420)


def submit(path, hint="", courses=None):
    """Run the full chain on one uploaded artefact."""
    if not os.path.exists(path):
        return None, f"no such file: {path}"
    kind = _kind(path)
    if not kind:
        return None, f"unsupported type {os.path.splitext(path)[1]}"
    os.makedirs(LIB, exist_ok=True)

    with open(path, "rb") as f:
        sid = hashlib.sha1(f.read()).hexdigest()[:12]
    with LOCK, _c() as c:
        prior = c.execute("SELECT status FROM kb_source WHERE id=?", (sid,)).fetchone()
        if prior and prior["status"] == "filed":
            return {"id": sid, "status": "already in library"}, None
        if prior:
            # a chain that died partway must not block the retry
            c.execute("DELETE FROM kb_card WHERE source_id=?", (sid,))
            c.execute("DELETE FROM kb_source WHERE id=?", (sid,))

    safe = sid + os.path.splitext(path)[1].lower()
    stored = os.path.join(LIB, safe)
    shutil.copy2(path, stored)
    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("""INSERT INTO kb_source(id,filename,kind,note,status,created,updated)
                     VALUES(?,?,?,?,?,?,?)""", (sid, safe, kind, hint[:400], "curating", now, now))

    meta, err = _curate(stored, kind, hint)
    if err:
        _fail(sid, "curate: " + err); return None, "curate: " + err
    if courses:
        meta["courses"] = list(courses)
    valid = set(_valid_courses())
    meta["courses"] = [c for c in (meta.get("courses") or []) if c in valid]
    with LOCK, _c() as c:
        c.execute("""UPDATE kb_source SET title=?,kind=?,summary=?,courses=?,discipline=?,
                     topics=?,status=?,updated=? WHERE id=?""",
                  (str(meta.get("title", ""))[:200], str(meta.get("kind", kind))[:20],
                   str(meta.get("summary", ""))[:600], json.dumps(meta["courses"]),
                   str(meta.get("discipline", ""))[:60],
                   json.dumps([str(t)[:60] for t in (meta.get("topics") or [])][:10]),
                   "extracting", now, sid))

    raw, err = _extract(stored, kind, meta)
    if err:
        _fail(sid, "extract: " + err); return None, "extract: " + err
    cards = []
    for d in raw:
        claim = llm.pick(d, "claim", "statement", "fact", "text")
        if not claim:
            continue
        k = str(llm.pick(d, "kind", "type", default="fact")).lower()
        try:
            conf = float(llm.pick(d, "confidence", default=0.7))
        except (TypeError, ValueError):
            conf = 0.7
        cards.append({"kind": k if k in CARD_KINDS else "fact",
                      "topic": str(llm.pick(d, "topic", "subject"))[:60],
                      "claim": str(claim)[:600],
                      "detail": str(llm.pick(d, "detail", "explanation", "notes"))[:2000],
                      "confidence": max(0.05, min(0.99, conf))})
    cards, junk = _drop_file_noise(cards)
    if not cards:
        _fail(sid, "extract: only file-mechanics noise, no subject content")
        return None, ("the extractor described the file rather than its content "
                      f"({junk} such claims dropped) — re-run, or convert it to an image")

    with LOCK, _c() as c:
        c.execute("UPDATE kb_source SET status=? WHERE id=?", ("verifying", sid))
    checks, err = _verify(cards, meta)
    if err:                       # a failed check must not pass as a clean bill
        checks = []
    by_i = {}
    for ch in (checks or []):
        try:
            by_i[int(llm.pick(ch, "i", "index", default=-1))] = ch
        except (TypeError, ValueError):
            pass

    tally = {}
    for i, card in enumerate(cards):
        ch = by_i.get(i) or {}
        verdict = str(llm.pick(ch, "verdict", "status", default="unchecked")).lower()
        if verdict not in ("verified", "corrected", "disputed", "unclear"):
            verdict = "unchecked"
        if verdict == "corrected":
            fixed = llm.pick(ch, "corrected_claim", "correction", "corrected")
            if fixed:
                card["claim"] = str(fixed)[:600]
        card["verdict"] = verdict
        card["note"] = str(llm.pick(ch, "note", "reason"))[:400]
        tally[verdict] = tally.get(verdict, 0) + 1

    primary = (meta["courses"] or [""])[0]
    with LOCK, _c() as c:
        for card in cards:
            c.execute("""INSERT INTO kb_card(source_id,course,topic,kind,claim,detail,
                         confidence,verdict,verifier_note,created)
                         VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      (sid, primary, card["topic"], card["kind"], card["claim"],
                       card["detail"], card["confidence"], card["verdict"],
                       card["note"], now))
        c.execute("UPDATE kb_source SET status=?,cards=?,updated=? WHERE id=?",
                  ("filed", len(cards), int(time.time()), sid))

    return {"id": sid, "title": meta.get("title"), "kind": meta.get("kind"),
            "courses": meta["courses"], "topics": meta.get("topics"),
            "cards": len(cards), "verdicts": tally,
            "disputed": [c["claim"][:140] for c in cards if c["verdict"] == "disputed"]}, None


# ──────────────────────────────────────────────────────── the interview
# Some context only the operator has: which lecture this came from, what the
# instructor stressed, whether it's testable. Asking them to volunteer it means
# asking them to already know what matters. So the agent asks - it knows what a
# gap in its own filing looks like, and the operator only has to answer.
def interview(source_id):
    """Agent generates the specific questions it needs answered about a source."""
    with LOCK, _c() as c:
        s = c.execute("SELECT * FROM kb_source WHERE id=?", (source_id,)).fetchone()
    if not s:
        return None, f"no source {source_id!r}"
    cs = cards(limit=400)
    mine = [c for c in cs if c["source_id"] == source_id]
    listing = "\n".join(f"- [{c['verdict']}] {c['claim'][:180]}" for c in mine[:30])
    system = (
        "You are the Curator for a nursing student's knowledge library. You have "
        "already read and filed the artefact below. Now ask the student what only "
        "they can tell you.\n" + GUARD + "\n\n"
        f"ARTEFACT: {s['title']} ({s['kind']})\n{s['summary']}\n"
        f"Filed under: {s['courses']} / {s['topics']}\n\n"
        f"WHAT YOU EXTRACTED:\n{listing}\n\n"
        "Ask 3-5 questions whose answers would materially change how this is filed or "
        "taught - the provenance you cannot infer, the emphasis their instructor placed "
        "on it, whether it is testable, which part confused them. Do NOT ask anything "
        "you could work out yourself from the artefact. Each question must be answerable "
        "in a sentence, and say plainly why you are asking.\n\n"
        'Return ONLY JSON: [{"q":"the question","why":"what it would change",'
        '"suggest":["a plausible answer","another"]}]')
    data, err = llm.ask_json(system, "Ask your questions.", want="array", timeout=240)
    if err:
        return None, err
    qs = []
    for d in data:
        q = llm.pick(d, "q", "question")
        if q:
            qs.append({"q": str(q)[:300], "why": str(llm.pick(d, "why", "reason"))[:200],
                       "suggest": [str(x)[:80] for x in (llm.pick(d, "suggest", "options",
                                                                  default=[]) or [])][:4]})
    return {"source_id": source_id, "title": s["title"], "questions": qs}, None


def answer(source_id, pairs):
    """Fold the student's answers back into the filing. `pairs` = [(q, a), ...]."""
    with LOCK, _c() as c:
        s = c.execute("SELECT * FROM kb_source WHERE id=?", (source_id,)).fetchone()
    if not s:
        return None, f"no source {source_id!r}"
    qa = "\n".join(f"Q: {q}\nA: {a}" for q, a in pairs if str(a).strip())
    if not qa:
        return None, "no answers given"
    system = (
        "You are the Curator. The student answered your questions about this artefact. "
        "Revise the filing accordingly.\n" + GUARD + "\n\n"
        "COURSES:\n" + _catalogue() + "\n\n"
        f"CURRENT FILING\ntitle: {s['title']}\nsummary: {s['summary']}\n"
        f"courses: {s['courses']}\ntopics: {s['topics']}\n\n"
        "Return the corrected filing, plus anything their answers revealed about them "
        "as a learner (only if genuinely evidenced - an empty list is fine).\n\n"
        'Return ONLY JSON: {"title":"...","summary":"...","courses":["A300"],'
        '"topics":["..."],"emphasis":"what to stress when teaching this, or empty",'
        '"learner":[{"kind":"gap|strength|preference","fact":"one sentence"}]}')
    data, err = llm.ask_json(system, qa[:8000], want="object", timeout=240)
    if err:
        return None, err
    valid = set(_valid_courses())
    courses = [c for c in (data.get("courses") or []) if c in valid] or json.loads(s["courses"] or "[]")
    note = (s["note"] or "")
    if data.get("emphasis"):
        note = (note + "\nEMPHASIS: " + str(data["emphasis"]))[:1000]
    with LOCK, _c() as c:
        c.execute("""UPDATE kb_source SET title=?,summary=?,courses=?,topics=?,note=?,
                     updated=? WHERE id=?""",
                  (str(data.get("title") or s["title"])[:200],
                   str(data.get("summary") or s["summary"])[:600], json.dumps(courses),
                   json.dumps([str(t)[:60] for t in (data.get("topics") or [])][:10]),
                   note, int(time.time()), source_id))
        if courses:
            c.execute("UPDATE kb_card SET course=? WHERE source_id=?", (courses[0], source_id))
    learned = []
    for f in (data.get("learner") or []):
        fact = llm.pick(f, "fact", "note")
        if not fact:
            continue
        try:
            import learner as _lm
            k = str(llm.pick(f, "kind", default="pattern")).lower()
            _lm.add_fact(k if k in _lm.KINDS else "pattern", courses[0] if courses else "",
                         str(fact), f"intake interview on {source_id}", 0.6)
            learned.append(str(fact))
        except Exception:
            pass
    return {"source_id": source_id, "courses": courses,
            "emphasis": data.get("emphasis", ""), "learned": learned}, None


# When a read goes wrong the extractor starts describing the artefact as a FILE -
# "the content stream is FlateDecode", "the filename is a hex identifier". None of
# that is nursing knowledge, and once filed it pollutes every later recall. Cheap
# deterministic filter; no model call.
_NOISE = ("flatedecode", "content stream", "pdftoppm", "poppler", "zlib",
          "the filename is", "file extension", "byte", "encoding is", "sha-1",
          "sha1", "hex identifier", "page count", "pdf metadata", "the read tool",
          "cannot be extracted", "extraction failure", "cat command", "utf-8",
          "base64", "mime type", "file size",
          # metadata about the artefact rather than what it teaches
          "the pdf ", "pdf title", "pdf author", "pdf was created", "document author",
          "creation date", "was created on",
          # the model narrating our own pipeline or this machine back at us
          "intake chain", "curator", "extractor", "verifier", "librarian stage",
          "terminal", "python one-liner", "one-liner", "approving", "permission",
          "c:\\users", "ecosystem")


def _drop_file_noise(cards):
    keep, dropped = [], 0
    for c in cards:
        hay = (c["claim"] + " " + (c["topic"] or "")).lower()
        if any(w in hay for w in _NOISE):
            dropped += 1
            continue
        keep.append(c)
    return keep, dropped


def _valid_courses():
    import nursing_api
    return list(nursing_api.COURSES)


def _fail(sid, why):
    with LOCK, _c() as c:
        c.execute("UPDATE kb_source SET status=?,note=?,updated=? WHERE id=?",
                  ("failed", why[:400], int(time.time()), sid))


# ────────────────────────────────────────────────────────────── reading
def sources(course=None, limit=100):
    q = "SELECT * FROM kb_source"; a = []
    if course:
        q += " WHERE courses LIKE ?"; a = [f'%"{course}"%']
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY created DESC LIMIT ?", a + [limit])]


def cards(course=None, topic=None, verdict=None, limit=200):
    q = "SELECT * FROM kb_card WHERE 1=1"; a = []
    if course:
        q += " AND course=?"; a.append(course)
    if topic:
        q += " AND topic LIKE ?"; a.append(f"%{topic}%")
    if verdict:
        q += " AND verdict=?"; a.append(verdict)
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(
            q + " ORDER BY (verdict='verified') DESC, confidence DESC LIMIT ?", a + [limit])]


def recall(query, course=None, limit=8):
    """Keyword retrieval over the library. Deterministic - no model call.

    Scores on distinctive words rather than raw overlap so that a query like
    'potassium ECG changes' does not rank every card containing 'the'.
    """
    words = [w for w in re.split(r"[^a-z0-9]+", (query or "").lower()) if len(w) > 3]
    if not words:
        return []
    scored = []
    for c in cards(course=course, limit=600):
        if c["verdict"] == "disputed":
            continue
        hay = (c["claim"] + " " + (c["detail"] or "") + " " + (c["topic"] or "")).lower()
        score = sum(3 if w in (c["topic"] or "").lower() else 1 for w in words if w in hay)
        if c["verdict"] == "verified":
            score += 1
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]


def brief(query, course=None, limit=6):
    """The library string other agents prepend. Cites the source it came from."""
    hits = recall(query, course, limit)
    if not hits:
        return ""
    with LOCK, _c() as c:
        titles = {r["id"]: r["title"] for r in c.execute("SELECT id,title FROM kb_source")}
    lines = ["FROM YOUR UPLOADED LIBRARY (material the student supplied; prefer it "
             "over generic phrasing, and cite it as 'your <source>'):"]
    for h in hits:
        tag = titles.get(h["source_id"]) or "upload"
        flag = "" if h["verdict"] == "verified" else f" [{h['verdict']}]"
        lines.append(f"  - {h['claim']}{flag}  (source: {tag})")
        if h["detail"]:
            lines.append(f"      {h['detail'][:220]}")
    return "\n".join(lines)


def dashboard():
    with LOCK, _c() as c:
        src = c.execute("SELECT COUNT(*) n, SUM(status='filed') filed FROM kb_source").fetchone()
        tot = c.execute("SELECT COUNT(*) n FROM kb_card").fetchone()["n"]
        by_v = {r["verdict"]: r["n"] for r in c.execute(
            "SELECT verdict, COUNT(*) n FROM kb_card GROUP BY verdict")}
        by_c = {r["course"]: r["n"] for r in c.execute(
            "SELECT course, COUNT(*) n FROM kb_card GROUP BY course")}
        recent = [dict(r) for r in c.execute(
            "SELECT id,title,kind,cards,status,created FROM kb_source ORDER BY created DESC LIMIT 8")]
    return {"sources": src["n"], "filed": src["filed"] or 0, "cards": tot,
            "verdicts": by_v, "by_course": by_c, "recent": recent}


if __name__ == "__main__":
    init()
    print(json.dumps(dashboard(), indent=2))
