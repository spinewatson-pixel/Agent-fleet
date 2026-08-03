"""The learner model - what the agents know about *you*, and how it deepens.

Every practice question is a small workspace, not a throwaway. You can open it,
argue with the tutor about it, keep notes on it, or tell it to rewrite itself.
All of that is evidence. `ingest()` is the agent that reads the evidence and
updates a profile; every other agent in the nursing stack reads that profile
before it writes anything, so the material bends toward you over time.

Two things evolve independently:

  PROFILE  facts about how you think - a misconception you keep repeating, a
           topic you're solid on, the explanation style that lands. Written by
           the ingest agent, never by hand.
  DEPTH    a per-topic level, 1-5. Rises when you demonstrate command of a topic
           and falls when you don't. Generation and tutoring both read it, so a
           topic you have mastered stops producing recall questions and starts
           producing multi-step clinical judgement ones.

The profile is stated evidence, not inference for its own sake: each fact
carries the observation that produced it, so a wrong read can be traced and
dropped rather than quietly steering everything forever.
"""
import json, os, re, sqlite3, threading, time

import llm

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS lm_profile(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, subject TEXT, fact TEXT,
  evidence TEXT, confidence REAL, hits INTEGER DEFAULT 1, active INTEGER DEFAULT 1,
  created INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS lm_depth(
  course TEXT, topic TEXT, level INTEGER, seen INTEGER, right_ INTEGER,
  updated INTEGER, PRIMARY KEY(course, topic));
CREATE TABLE IF NOT EXISTS lm_chat(
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, course TEXT, role TEXT,
  text TEXT, saved INTEGER DEFAULT 0, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_lm_chat ON lm_chat(item_id, id);
CREATE TABLE IF NOT EXISTS lm_note(
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, course TEXT, text TEXT,
  created INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS lm_revision(
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, course TEXT, instruction TEXT,
  before TEXT, after TEXT, created INTEGER);
CREATE TABLE IF NOT EXISTS lm_ingest(
  id INTEGER PRIMARY KEY AUTOINCREMENT, upto INTEGER, found INTEGER,
  summary TEXT, created INTEGER);
"""

KINDS = ("misconception", "gap", "strength", "preference", "pattern")

GUARD = ("This is NCLEX exam preparation for a nursing student, not clinical guidance "
         "for a real patient. If you are unsure of a clinical specific - a dose, a lab "
         "value, a protocol - say so rather than stating it confidently.")


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


# ─────────────────────────────────────────────────────────── profile
def profile(kinds=None, limit=60):
    q = "SELECT * FROM lm_profile WHERE active=1"
    a = []
    if kinds:
        q += " AND kind IN (%s)" % ",".join("?" * len(kinds)); a += list(kinds)
    q += " ORDER BY confidence*hits DESC, updated DESC LIMIT ?"; a.append(limit)
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q, a)]


def brief(course=None, limit=14):
    """The compact profile string every nursing agent gets prepended.

    Kept short on purpose - a long profile dilutes the actual task, and the
    highest-signal facts are the ones with repeated evidence anyway.
    """
    rows = profile(limit=limit * 3)
    if course:
        rows.sort(key=lambda r: (course not in (r["subject"] or ""), -r["confidence"] * r["hits"]))
    rows = rows[:limit]
    if not rows:
        return ""
    by = {}
    for r in rows:
        by.setdefault(r["kind"], []).append(f"{r['subject']}: {r['fact']}" if r["subject"] else r["fact"])
    order = ["misconception", "gap", "strength", "preference", "pattern"]
    out = ["WHAT YOU KNOW ABOUT THIS STUDENT (from their own work - use it, don't recite it):"]
    for k in order:
        if by.get(k):
            out.append(f"  {k}: " + "; ".join(by[k][:5]))
    return "\n".join(out)


def add_fact(kind, subject, fact, evidence, confidence=0.6):
    """Upsert - a fact seen again gains weight rather than duplicating."""
    now = int(time.time())
    key = re.sub(r"[^a-z0-9 ]", "", fact.lower())[:70]
    with LOCK, _c() as c:
        for r in c.execute("SELECT id,fact,hits,confidence FROM lm_profile WHERE kind=? AND active=1",
                           (kind,)).fetchall():
            if re.sub(r"[^a-z0-9 ]", "", r["fact"].lower())[:70] == key:
                c.execute("UPDATE lm_profile SET hits=hits+1,confidence=?,evidence=?,updated=? WHERE id=?",
                          (min(0.98, r["confidence"] + 0.12), evidence[:500], now, r["id"]))
                return r["id"]
        cur = c.execute("""INSERT INTO lm_profile(kind,subject,fact,evidence,confidence,created,updated)
                           VALUES(?,?,?,?,?,?,?)""",
                        (kind, (subject or "")[:60], fact[:300], (evidence or "")[:500],
                         confidence, now, now))
        return cur.lastrowid


def drop_fact(fid):
    with LOCK, _c() as c:
        c.execute("UPDATE lm_profile SET active=0 WHERE id=?", (fid,))


# ───────────────────────────────────────────────────────────── depth
def depth(course, topic):
    with LOCK, _c() as c:
        r = c.execute("SELECT level FROM lm_depth WHERE course=? AND topic=?",
                      (course, topic)).fetchone()
    return r["level"] if r else 1


DEPTH_WORDS = {
    1: "foundational - define the concept and its mechanism plainly",
    2: "applied - recognise it in a straightforward patient presentation",
    3: "analytical - distinguish it from the conditions it is confused with",
    4: "clinical judgement - prioritise among several plausible actions",
    5: "expert - multi-system, conflicting data, delegation and escalation",
}


def depth_hint(course, topic):
    lv = depth(course, topic)
    return f"Target depth {lv}/5 for '{topic}': {DEPTH_WORDS[lv]}."


def bump(course, topic, correct):
    """Track command of a topic and move the level when the evidence is clear."""
    now = int(time.time())
    with LOCK, _c() as c:
        r = c.execute("SELECT * FROM lm_depth WHERE course=? AND topic=?",
                      (course, topic)).fetchone()
        if not r:
            c.execute("INSERT INTO lm_depth VALUES(?,?,?,?,?,?)",
                      (course, topic, 1, 1, 1 if correct else 0, now))
            return 1
        seen, right = r["seen"] + 1, r["right_"] + (1 if correct else 0)
        lv = r["level"]
        # three of the last few right -> up; sustained miss rate -> down
        if seen >= 3 and right / seen >= 0.8 and lv < 5:
            lv, seen, right = lv + 1, 0, 0
        elif seen >= 4 and right / seen < 0.4 and lv > 1:
            lv, seen, right = lv - 1, 0, 0
        c.execute("UPDATE lm_depth SET level=?,seen=?,right_=?,updated=? WHERE course=? AND topic=?",
                  (lv, seen, right, now, course, topic))
        return lv


def depth_map(course=None):
    q = "SELECT * FROM lm_depth"; a = []
    if course:
        q += " WHERE course=?"; a = [course]
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY level DESC, topic", a)]


# ────────────────────────────────────────────────────────── the chat
def _item(item_id):
    with LOCK, _c() as c:
        r = c.execute("SELECT * FROM nursing_items WHERE id=?", (item_id,)).fetchone()
    return dict(r) if r else None


def _item_text(it):
    opts = json.loads(it["options"] or "[]")
    lines = [it["stem"]]
    for i, o in enumerate(opts):
        mark = " (correct)" if i == it["correct"] else ""
        lines.append(f"  {chr(65+i)}. {o}{mark}")
    lines.append("Rationale: " + (it["rationale"] or ""))
    return "\n".join(lines)


def history(item_id, limit=40):
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(
            "SELECT id,role,text,saved,created FROM lm_chat WHERE item_id=? ORDER BY id LIMIT ?",
            (item_id, limit))]


def chat(item_id, message):
    """Talk to the tutor about one specific question."""
    it = _item(item_id)
    if not it:
        return None, f"no item {item_id!r}"
    import nursing_api
    co = nursing_api.COURSES.get(it["course"]) or {}
    prior = history(item_id)
    notes = get_notes(item_id)
    system = (
        f"You are the course expert for {co.get('name', it['course'])} ({it['course']}), "
        "sitting with the student going over one practice question.\n" + GUARD + "\n\n"
        f"THE QUESTION\n{_item_text(it)}\n\n"
        + (f"THEIR NOTES ON IT\n{notes}\n\n" if notes else "")
        + brief(it["course"]) + "\n\n"
        + depth_hint(it["course"], it["topic"] or "general") + "\n\n"
        "Teach, don't lecture. Answer what they actually asked in a few short "
        "paragraphs. If their reasoning is wrong, name the specific wrong step "
        "rather than restating the right answer. If they're right, say so and push "
        "one level deeper."
    )
    convo = "\n\n".join(f"{r['role'].upper()}: {r['text']}" for r in prior[-8:])
    user = (convo + "\n\nSTUDENT: " + message) if convo else message
    text, err = llm.ask(system, user, timeout=180)
    if err:
        return None, err
    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("INSERT INTO lm_chat(item_id,course,role,text,created) VALUES(?,?,?,?,?)",
                  (item_id, it["course"], "student", message, now))
        c.execute("INSERT INTO lm_chat(item_id,course,role,text,created) VALUES(?,?,?,?,?)",
                  (item_id, it["course"], "tutor", text, now))
    return {"item_id": item_id, "reply": text}, None


def save_chat(item_id, on=True):
    """Mark a thread worth keeping. Saved threads are weighted in ingest."""
    with LOCK, _c() as c:
        c.execute("UPDATE lm_chat SET saved=? WHERE item_id=?", (1 if on else 0, item_id))
    return {"item_id": item_id, "saved": bool(on)}


# ───────────────────────────────────────────────────────────── notes
def get_notes(item_id):
    with LOCK, _c() as c:
        r = c.execute("SELECT text FROM lm_note WHERE item_id=? ORDER BY id DESC LIMIT 1",
                      (item_id,)).fetchone()
    return r["text"] if r else ""


def note(item_id, text):
    it = _item(item_id)
    now = int(time.time())
    with LOCK, _c() as c:
        r = c.execute("SELECT id FROM lm_note WHERE item_id=?", (item_id,)).fetchone()
        if r:
            c.execute("UPDATE lm_note SET text=?,updated=? WHERE id=?", (text, now, r["id"]))
        else:
            c.execute("INSERT INTO lm_note(item_id,course,text,created,updated) VALUES(?,?,?,?,?)",
                      (item_id, (it or {}).get("course", ""), text, now, now))
    return {"item_id": item_id, "saved": True}


# ────────────────────────────────────────────────────────── revision
def revise(item_id, instruction):
    """Rewrite a question to the student's instruction. Keeps the old version."""
    it = _item(item_id)
    if not it:
        return None, f"no item {item_id!r}"
    import nursing_api
    co = nursing_api.COURSES.get(it["course"]) or {}
    system = (
        f"You are the item writer for {co.get('name', it['course'])}.\n{GUARD}\n\n"
        f"CURRENT ITEM\n{_item_text(it)}\n\n" + brief(it["course"]) + "\n\n"
        "Rewrite it as the student asks. Keep it a legitimate NCLEX-style item: "
        "one unambiguously best answer, plausible distractors, a rationale that "
        "explains why the others are wrong too.\n\n"
        'Return ONLY JSON: {"stem":"...","options":["..","..","..",".."],'
        '"correct":0,"rationale":"...","topic":"...","difficulty":"easy|medium|hard"}')
    data, err = llm.ask_json(system, instruction, want="object", timeout=200)
    if err:
        return None, err
    opts = [str(o) for o in (data.get("options") or [])]
    if len(opts) < 3:
        return None, "revision returned too few options"
    try:
        correct = int(data.get("correct", 0))
    except (TypeError, ValueError):
        correct = 0
    correct = max(0, min(correct, len(opts) - 1))
    before = _item_text(it)
    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("""UPDATE nursing_items SET stem=?,options=?,correct=?,rationale=?,
                     topic=?,difficulty=? WHERE id=?""",
                  (str(data.get("stem", it["stem"]))[:900], json.dumps(opts), correct,
                   str(data.get("rationale", ""))[:2000],
                   str(data.get("topic") or it["topic"])[:48],
                   str(data.get("difficulty") or it["difficulty"])[:10], item_id))
        c.execute("""INSERT INTO lm_revision(item_id,course,instruction,before,after,created)
                     VALUES(?,?,?,?,?,?)""",
                  (item_id, it["course"], instruction[:400], before,
                   _item_text(_item(item_id) or it), now))
    add_fact("preference", it["course"],
             f"asked for items to be rewritten: {instruction[:120]}",
             f"revision of {item_id}", 0.5)
    return _item(item_id), None


def revisions(item_id):
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM lm_revision WHERE item_id=? ORDER BY id DESC", (item_id,))]


# ──────────────────────────────────────────────────────────── ingest
def _evidence(since):
    """Everything the student has produced since the last ingest."""
    with LOCK, _c() as c:
        chats = [dict(r) for r in c.execute(
            """SELECT item_id,course,role,text,saved FROM lm_chat
               WHERE created>? ORDER BY id LIMIT 120""", (since,))]
        notes = [dict(r) for r in c.execute(
            "SELECT item_id,course,text FROM lm_note WHERE updated>? LIMIT 40", (since,))]
        revs = [dict(r) for r in c.execute(
            "SELECT item_id,course,instruction FROM lm_revision WHERE created>? LIMIT 30", (since,))]
        wrong = [dict(r) for r in c.execute(
            """SELECT a.course,a.topic,i.stem,i.rationale FROM nursing_answers a
               LEFT JOIN nursing_items i ON i.id=a.item_id
               WHERE a.created>? AND a.correct=0 ORDER BY a.id DESC LIMIT 40""", (since,))]
    return chats, notes, revs, wrong


def ingest():
    """Read recent work, update the profile. Operator-initiated, never scheduled."""
    with LOCK, _c() as c:
        r = c.execute("SELECT MAX(upto) u FROM lm_ingest").fetchone()
    since = (r["u"] if r and r["u"] else 0)
    now = int(time.time())
    chats, notes, revs, wrong = _evidence(since)
    if not (chats or notes or revs or wrong):
        return {"found": 0, "note": "nothing new since last ingest"}, None

    blob = []
    if wrong:
        blob.append("MISSED QUESTIONS:\n" + "\n".join(
            f"- [{w['course']}/{w['topic']}] {(w['stem'] or '')[:200]}" for w in wrong[:20]))
    if chats:
        blob.append("TUTOR CONVERSATIONS (student turns are the signal):\n" + "\n".join(
            f"- {'[saved] ' if ch['saved'] else ''}{ch['role']}: {ch['text'][:280]}"
            for ch in chats[:40]))
    if notes:
        blob.append("THEIR OWN NOTES:\n" + "\n".join(f"- {n['text'][:280]}" for n in notes))
    if revs:
        blob.append("REWRITES THEY ASKED FOR:\n" + "\n".join(
            f"- {v['instruction'][:200]}" for v in revs))

    system = (
        "You are the learning analyst for a nursing student's study system. Below is "
        "everything they produced since the last review. Infer what is true about how "
        "they think - the specific misconception behind a wrong answer, a topic they "
        "clearly command, the explanation style they respond to.\n\n"
        "Rules: be specific and falsifiable. 'Confuses right- and left-sided heart "
        "failure signs' is useful; 'needs to study cardiac' is not. Only claim what "
        "the evidence supports. Six facts maximum; fewer is fine.\n\n"
        'Return ONLY JSON: [{"kind":"misconception|gap|strength|preference|pattern",'
        '"subject":"course code or topic","fact":"one specific sentence",'
        '"evidence":"what in the material shows this","confidence":0.0-1.0}]')
    data, err = llm.ask_json(system, "\n\n".join(blob)[:14000], want="array", timeout=240)
    if err:
        return None, err

    added = []
    for f in data:
        if not isinstance(f, dict) or not f.get("fact"):
            continue
        kind = str(f.get("kind", "pattern")).lower()
        if kind not in KINDS:
            kind = "pattern"
        try:
            conf = float(f.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6
        add_fact(kind, str(f.get("subject", "")), str(f["fact"]),
                 str(f.get("evidence", "")), max(0.1, min(0.98, conf)))
        added.append(f"{kind}: {f['fact']}")

    with LOCK, _c() as c:
        c.execute("INSERT INTO lm_ingest(upto,found,summary,created) VALUES(?,?,?,?)",
                  (now, len(added), json.dumps(added), now))
    return {"found": len(added), "facts": added,
            "evidence": {"chats": len(chats), "notes": len(notes),
                         "revisions": len(revs), "missed": len(wrong)}}, None


def dashboard():
    p = profile(limit=40)
    with LOCK, _c() as c:
        ing = c.execute("SELECT * FROM lm_ingest ORDER BY id DESC LIMIT 1").fetchone()
        chats = c.execute("SELECT COUNT(DISTINCT item_id) n FROM lm_chat").fetchone()["n"]
        notes = c.execute("SELECT COUNT(*) n FROM lm_note").fetchone()["n"]
        revs = c.execute("SELECT COUNT(*) n FROM lm_revision").fetchone()["n"]
    by = {}
    for f in p:
        by[f["kind"]] = by.get(f["kind"], 0) + 1
    dm = depth_map()
    return {"facts": len(p), "by_kind": by, "threads": chats, "notes": notes,
            "revisions": revs, "topics_tracked": len(dm),
            "avg_depth": round(sum(d["level"] for d in dm) / len(dm), 2) if dm else 0,
            "last_ingest": dict(ing) if ing else None,
            "top": [{"kind": f["kind"], "subject": f["subject"], "fact": f["fact"],
                     "confidence": round(f["confidence"], 2), "hits": f["hits"]} for f in p[:12]]}


if __name__ == "__main__":
    init()
    print(json.dumps(dashboard(), indent=2)[:1500])
