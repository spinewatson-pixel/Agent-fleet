"""Shared Claude CLI plumbing. Every module calls the model through here.

Hard-won details baked in (see ARCHITECTURE.md P1/P2):
  - --append-system-prompt, NEVER --system-prompt (the latter wipes tool scaffolding)
  - --permission-mode dontAsk, or tools silently no-op in headless mode
  - the user's question goes on stdin, never argv, so nothing can break out to a shell
  - stdout decoded as utf-8 explicitly; Windows would otherwise use cp1252
"""
import json, os, re, shutil, subprocess

TIMEOUT = 180


def argv_base():
    exe = shutil.which("claude")
    if not exe:
        return None
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe]          # CreateProcess can't run .cmd directly
    return [exe]


def ask(system, user, web=False, timeout=TIMEOUT, tools=""):
    """Returns (text, error). Either may be None."""
    base = argv_base()
    if not base:
        return None, "claude CLI not found on PATH"
    allowed = "WebSearch,WebFetch" if web else tools
    argv = base + [
        "-p",
        "--append-system-prompt", system,
        "--no-session-persistence",
        "--permission-mode", "dontAsk",
        "--allowed-tools", allowed,
        "--disallowed-tools", "Bash,Edit,Write,NotebookEdit,Task",
    ]
    try:
        p = subprocess.run(argv, input=user, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return None, "timed out"
    except Exception as e:
        return None, type(e).__name__
    if p.returncode != 0:
        return None, (p.stderr or "cli error").strip()[:200]
    out = (p.stdout or "").strip()
    return (out or None), (None if out else "empty output")


def json_blocks(text):
    """Every balanced {...} or [...] in the text, in order."""
    out, depth, start, opener = [], 0, None, None
    for i, ch in enumerate(text or ""):
        if ch in "{[":
            if depth == 0:
                start, opener = i, ch
            depth += 1
        elif ch in "}]" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                out.append(text[start:i + 1])
    return out


def ask_json(system, user, want="object", web=False, timeout=TIMEOUT, retries=1, tools=""):
    """Ask for JSON and actually get it.

    Models reliably ignore format contracts (P2), so this asks, then distils with
    a second narrow call if the first reply came back as prose.
    """
    strict = (system + "\n\nOutput ONLY valid JSON and nothing else — no prose, no "
              "markdown, no code fence.")
    # Restated in the user turn as well. System-prompt instructions get diluted:
    # calls have come back asking what structure was wanted while the schema sat
    # in their system prompt. The user turn is the one that reliably lands.
    tail = ("\n\nRespond with valid JSON only — no prose before or after it, and no "
            "offer of further help.")
    text, err = ask(strict, (user or "") + tail, web=web, timeout=timeout, tools=tools)
    if err:
        return None, err

    for attempt in range(retries + 1):
        for blk in reversed(json_blocks(text)):
            try:
                v = json.loads(blk)
            except Exception:
                continue
            if want == "array":
                if isinstance(v, list):
                    return v, None
                # models like to wrap: {"foundations":[...]} — take the sole list
                if isinstance(v, dict):
                    lists = [x for x in v.values() if isinstance(x, list)]
                    if len(lists) == 1:
                        return lists[0], None
            if want == "object":
                if isinstance(v, dict):
                    return v, None
                if isinstance(v, list) and len(v) == 1 and isinstance(v[0], dict):
                    return v[0], None
        if attempt >= retries:
            break
        # distil: hand the prose back and ask only for the structure
        shape = "a JSON array" if want == "array" else "a single JSON object"
        text, err = ask(
            "Output ONLY " + shape + " and nothing else — no prose, no markdown, no "
            "code fence. Convert the content below into that structure faithfully. "
            "Invent nothing that is not present.",
            (text or "")[:6000], timeout=120)
        if err:
            return None, err
    return None, "no parseable JSON"


def read_then_json(read_system, read_user, want_shape, want="object",
                   tools="Read", timeout=TIMEOUT):
    """Two passes: look at the artefact, then structure what was seen.

    A model that has just used a tool reports back conversationally — it will
    describe a PDF beautifully and ignore "output only JSON" completely. Asking
    for both at once loses the reading. So the first call is allowed to be prose
    (that is its job), and a second call with no tools turns that prose into the
    shape we need. Slower by one call, but it stops throwing away good reads.
    """
    seen, err = ask(read_system, read_user, timeout=timeout, tools=tools)
    if err:
        return None, err, None
    # The schema goes in the USER turn, not the system prompt. Appended system
    # text gets diluted — a distil call was observed replying "no target
    # structure has been provided" with the schema sitting in its system prompt,
    # then inventing a whole catalogue that was never in the input. In the user
    # turn it is unmissable.
    data, jerr = ask_json(
        "You convert descriptions into JSON. Use ONLY facts present in the "
        "description you are given. If a field has no support in the text, use an "
        "empty string or empty list — never fill it in from your own knowledge.",
        "TARGET STRUCTURE:\n" + want_shape + "\n\nDESCRIPTION TO CONVERT:\n"
        + seen[:14000] + "\n\nReturn only the JSON.",
        want=want, timeout=min(timeout, 240))
    return data, jerr, seen


def pick(d, *names, default=""):
    """First non-empty value among several plausible key names.

    Models substitute synonyms freely — `concept` comes back as `name` or
    `title` often enough that demanding one exact key throws away good data.
    """
    if not isinstance(d, dict):
        return default
    low = {str(k).lower(): v for k, v in d.items()}
    for n in names:
        v = low.get(n.lower())
        if v not in (None, "", [], {}):
            return v
    return default


def clean_id(s, limit=24):
    return re.sub(r"[^A-Z0-9\-]", "", str(s or "").upper())[:limit]
