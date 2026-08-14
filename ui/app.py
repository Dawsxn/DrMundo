"""Streamlit chat UI for Dr. Mundo.

One conversation, no sidebar. The patient drags a photo of their doctor's request into
the chat box; Dr. Mundo says what it read, then walks through the remaining questions
using real controls rather than asking them to describe things in prose. The figure and
the PDF arrive together at the end.

Three things are deliberate:

  Questions are answered by clicking, not typing. A patient offered the actual candidate
  tests picks the right one; the same patient asked to describe the difference in free
  text often cannot. Typing still works for anyone who prefers it.

  No price appears mid-intake. A half-answered estimate is the one most likely to be
  wrong in the direction that costs the patient money.

  The uploaded photo stays in the conversation and opens full size, so they can check we
  read the right piece of paper before trusting a number that came off it.

Run the API first:  uvicorn api.main:app --reload
Then this UI:       streamlit run ui/app.py
"""

import base64
import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("DR_MUNDO_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 120          # the reader makes a vision call; give it room.

st.set_page_config(page_title="Dr. Mundo: PH Medical Cost Estimator",
                   page_icon="🩺", layout="centered",
                   initial_sidebar_state="collapsed")

SAMPLES = [
    "Magkano ang tanggal apdo?",
    "How much is a lipid profile?",
    "Magkano ang CBC?",
    "Magkano ang creatinine?",
]


# ----------------------------------------------------------------- theme
def _inject_theme() -> None:
    # White everywhere, including the bottom chat bar: Streamlit paints that container
    # separately from the app background, so it needs its own rule or it stays grey.
    # Keep this block free of blank lines -- the Markdown renderer ends a raw-HTML block
    # at the first one and would spill the CSS onto the page as text.
    st.markdown(
        """<style>
:root{--ink:#0f172a;--mute:#64748b;--line:#e2e8f0;--accent:#0e7490;--accent-soft:#ecfeff;}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"],[data-testid="stMain"],[data-testid="stBottomBlockContainer"],[data-testid="stBottom"],[data-testid="stBottom"] > div{background:#ffffff !important;}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none !important;}
[data-testid="stHeader"]{height:0 !important;}
[data-testid="stMainBlockContainer"]{padding-top:2.2rem;padding-bottom:5rem;max-width:44rem;}
.stApp,[data-testid="stMarkdownContainer"],p,li,label,h1,h2,h3,h4{color:var(--ink);}
[data-testid="stChatMessage"]{background:transparent !important;border:0 !important;box-shadow:none !important;padding:2px 0 !important;}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p{margin-bottom:.35rem;line-height:1.55;}
[data-testid="stChatInput"]{border:1px solid var(--line) !important;border-radius:14px !important;background:#fff !important;box-shadow:0 1px 3px rgba(15,23,42,.06);}
[data-testid="stChatInput"]:focus-within{border-color:var(--accent) !important;box-shadow:0 0 0 3px rgba(14,116,144,.10);}
.stButton > button{border:1px solid var(--line) !important;background:#fff !important;color:var(--ink) !important;border-radius:10px !important;font-weight:500;padding:.42rem .8rem;transition:all .14s ease;}
.stButton > button:hover{border-color:var(--accent) !important;color:var(--accent) !important;background:var(--accent-soft) !important;}
.stButton > button[kind="primary"]{background:var(--accent) !important;color:#fff !important;border-color:var(--accent) !important;}
.stButton > button[kind="primary"]:hover{filter:brightness(1.08);color:#fff !important;}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input{border-radius:9px !important;}
[data-testid="stExpander"] details{border:1px solid var(--line) !important;border-radius:12px !important;background:#fff !important;box-shadow:none !important;}
[data-testid="stExpander"] summary{font-size:.9rem;color:var(--mute);}
[data-testid="stTable"] table{border:1px solid var(--line);border-radius:12px;font-size:.88rem;}
[data-testid="stTable"] th{background:#f8fafc !important;color:var(--mute) !important;font-weight:600;}
hr{border-color:var(--line);}
.dm-top .name{font-weight:700;font-size:1.02rem;letter-spacing:-.01em;}
.dm-top .sub{color:var(--mute);font-size:.8rem;}
.dm-hero{text-align:center;padding:14vh 0 1.2rem;}
.dm-hero h1{font-size:2.05rem;margin:.2rem 0;letter-spacing:-.02em;}
.dm-hero p{color:var(--mute);margin:.3rem auto 0;max-width:26rem;line-height:1.55;}
.dm-amount{font-size:2.15rem;font-weight:700;line-height:1.15;margin:.1rem 0 .7rem;color:var(--accent);letter-spacing:-.02em;}
.dm-amount-label{font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);}
.dm-note{color:var(--mute);font-size:.82rem;line-height:1.5;margin:.15rem 0;}
.dm-q{border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:.85rem 1rem .5rem;margin:.35rem 0 .6rem;background:#fcfeff;}
.dm-q .step{font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;color:var(--mute);}
.dm-q .ask{font-weight:600;margin:.15rem 0 .1rem;}
</style>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------- state
def _init_state() -> None:
    st.session_state.setdefault("session_id", uuid.uuid4().hex)
    st.session_state.setdefault("messages", [])    # {role, text, meta, image, pdf}
    st.session_state.setdefault("question", None)  # the pending intake question
    st.session_state.setdefault("has_slip", False)


def _new_chat() -> None:
    try:
        requests.post(f"{API_URL}/reset",
                      json={"session_id": st.session_state.session_id}, timeout=10)
    except requests.RequestException:
        pass
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []
    st.session_state.question = None
    st.session_state.has_slip = False


# ----------------------------------------------------------------- rendering
def _peso(v) -> str:
    """Money may arrive as a number or, for Decimal fields, as a JSON string."""
    if v is None or v == "":
        return "n/a"
    try:
        return f"₱{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


@st.dialog("Your request slip", width="large")
def _show_slip(image_bytes: bytes) -> None:
    st.image(image_bytes, use_container_width=True)


def _render_slip(image_bytes: bytes, key: str) -> None:
    cols = st.columns([1, 4])
    with cols[0]:
        st.image(image_bytes, use_container_width=True)
    with cols[1]:
        st.caption("Your request slip")
        if st.button("View full size", key=f"view_{key}"):
            _show_slip(image_bytes)


def _render_budget(answer: dict) -> None:
    budget = answer.get("budget")
    if not budget:
        return

    st.markdown(
        f'<div class="dm-amount-label">What you&rsquo;ll pay</div>'
        f'<div class="dm-amount">{_peso(budget.get("prepare_low"))} &ndash; '
        f'{_peso(budget.get("prepare_high"))}</div>',
        unsafe_allow_html=True,
    )

    priced = budget.get("priced") or []
    if priced:
        with st.expander(f"Priced ({len(priced)})", expanded=True):
            st.table([
                {"Test": p.get("catalog_name"),
                 "Price": f'{_peso(p.get("price_low"))} – {_peso(p.get("price_high"))}'}
                for p in priced
            ])

    # These never collapse away: an item quietly missing from a report is how an
    # understated bill becomes invisible.
    for key, title, note in (
        ("unpriced", "Not priced",
         "MMC publishes no price for these, so they are **not** in the total."),
        ("needs_confirmation", "Still unconfirmed",
         "I could not pin these down, so they are not priced."),
        ("cancelled", "Crossed out by your doctor",
         "Not ordered, so **not** charged."),
    ):
        items = budget.get(key) or []
        if items:
            with st.expander(f"{title} ({len(items)})", expanded=False):
                st.caption(note)
                for it in items:
                    st.markdown(f"- {it.get('normalized') or it.get('raw_text')}")

    for caveat in budget.get("caveats") or []:
        st.markdown(f'<div class="dm-note">{caveat}</div>', unsafe_allow_html=True)


def _fetch_pdf() -> bytes | None:
    try:
        resp = requests.get(f"{API_URL}/report.pdf",
                            params={"session_id": st.session_state.session_id},
                            timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return None
    return resp.content if resp.status_code == 200 else None


def _render_pdf(payload: bytes, key: str) -> None:
    """Inline preview plus a download, rendered in the conversation.

    Not in a sidebar: Streamlit draws the sidebar before the main area, so anything gated
    on state set while handling a turn is always a run behind.
    """
    if not payload:
        return
    cols = st.columns([2, 1])
    cols[0].download_button("Download the PDF", payload, key=f"dl_{key}",
                            file_name="dr-mundo-estimate.pdf", mime="application/pdf",
                            use_container_width=True, type="primary")
    if cols[1].button("Start over", key=f"restart_{key}", use_container_width=True):
        _new_chat()
        st.rerun()
    try:
        st.pdf(payload, height=560)
    except Exception:
        b64 = base64.b64encode(payload).decode()
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="560" '
            f'style="border:1px solid #e2e8f0;border-radius:12px"></iframe>',
            unsafe_allow_html=True,
        )


def _render_message(msg: dict, index: int) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("image"):
            _render_slip(msg["image"], key=f"m{index}")
        if msg.get("text"):
            st.markdown(msg["text"])
        meta = msg.get("meta")
        if msg["role"] == "assistant" and meta:
            answer = meta.get("answer") or {}
            if answer.get("budget"):
                _render_budget(answer)
                if msg.get("pdf"):
                    _render_pdf(msg["pdf"], key=f"m{index}")


# ----------------------------------------------------------------- the question card
def _render_question(q: dict) -> None:
    """The pending question, as controls.

    Clicking sends a deterministic choice to /choice, which never reaches the extractor.
    Anyone who would rather type can still use the chat box instead.
    """
    step, total = q.get("step", 0), q.get("total", 0)
    # Disambiguation repeats once per unclear item, so it gets its own wording rather
    # than sharing the main question count.
    noun = "Confirming" if q["kind"] == "disambiguate" else "Question"
    counter = f"{noun} {step} of {total}" if total else "One more thing"
    st.markdown(
        f'<div class="dm-q"><div class="step">{counter}</div>'
        f'<div class="ask">{q["text"]}</div></div>',
        unsafe_allow_html=True,
    )

    kind, options = q["kind"], q.get("options") or []
    extra_key = f"extra_{kind}_{step}"

    # The optional companion input: an operation name, or a remaining balance.
    extra = None
    if q.get("field") == "text" and kind == "procedure":
        extra = st.text_input("Which operation?", key=extra_key,
                              placeholder="If it is for an operation, name it here",
                              label_visibility="collapsed")
    elif q.get("field") == "number" and kind == "hmo":
        extra = st.text_input("Benefit remaining", key=extra_key,
                              placeholder="Benefit remaining, if you know it (e.g. 40000)",
                              label_visibility="collapsed")

    if options:
        cols = st.columns(min(len(options), 3))
        for i, option in enumerate(options):
            if cols[i % len(cols)].button(option, key=f"opt_{kind}_{step}_{i}",
                                          use_container_width=True):
                _send_choice(kind, option, extra)

    if st.button("Skip this", key=f"skip_{kind}_{step}"):
        _post_turn("/skip", echo="Skipped",
                   json={"session_id": st.session_state.session_id})


# ----------------------------------------------------------------- turns
def _post(path: str, **kwargs) -> dict | None:
    try:
        resp = requests.post(f"{API_URL}{path}", timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        st.error(f"Couldn't reach Dr. Mundo at `{API_URL}`. Is the API running?\n\n_{exc}_")
        return None
    if resp.status_code != 200:
        detail = ""
        try:
            detail = resp.json().get("detail", "")
        except ValueError:
            detail = resp.text[:200]
        st.error(detail or f"Something went wrong (HTTP {resp.status_code}).")
        return None
    return resp.json()


def _absorb(data: dict, echo: str | None = None) -> None:
    """Record a turn: the echoed user action, the reply, the next question, the PDF."""
    if echo:
        st.session_state.messages.append(
            {"role": "user", "text": echo, "meta": None, "image": None, "pdf": None})

    answer = data.get("answer") or {}
    pdf = _fetch_pdf() if answer.get("budget") else None
    st.session_state.messages.append(
        {"role": "assistant", "text": answer.get("answer_text", ""),
         "meta": data, "image": None, "pdf": pdf})
    st.session_state.question = data.get("question")


def _post_turn(path: str, echo: str | None = None, **kwargs) -> None:
    data = _post(path, **kwargs)
    if data is None:
        return
    _absorb(data, echo)
    st.rerun()


def _send_choice(kind: str, value: str, extra) -> None:
    payload = {"kind": kind, "value": value, "session_id": st.session_state.session_id}
    if extra:
        payload["extra"] = str(extra)
    echo = f"{value} — {extra}" if extra else value
    _post_turn("/choice", echo=echo, json=payload)


def _handle_slip(file) -> None:
    payload = file.getvalue()
    st.session_state.messages.append(
        {"role": "user", "text": "", "meta": None, "image": payload, "pdf": None})
    with st.spinner("Reading your request slip…"):
        data = _post("/ask-slip",
                     files={"file": (file.name, payload, file.type or "image/png")},
                     data={"session_id": st.session_state.session_id})
    if data is None:
        return
    st.session_state.has_slip = True
    _absorb(data)
    st.rerun()


def _handle_text(text: str) -> None:
    # With a slip in play, plain text is an answer to the pending question. Without one,
    # it is an ordinary cost question for the v1 path.
    endpoint = "/converse" if st.session_state.has_slip else "/ask"
    body = ({"text": text, "session_id": st.session_state.session_id}
            if endpoint == "/converse"
            else {"question": text, "session_id": st.session_state.session_id})
    with st.spinner("Checking the numbers…"):
        data = _post(endpoint, json=body)
    if data is None:
        return
    _absorb(data, echo=text)
    st.rerun()


# ----------------------------------------------------------------- app
_inject_theme()
_init_state()

if st.session_state.messages:
    top = st.columns([4, 1])
    top[0].markdown(
        '<div class="dm-top"><div class="name">Dr. Mundo 🩺</div>'
        '<div class="sub">Makati Medical Center &middot; published prices</div></div>',
        unsafe_allow_html=True,
    )
    if top[1].button("New chat", use_container_width=True):
        _new_chat()
        st.rerun()

    for i, msg in enumerate(st.session_state.messages):
        _render_message(msg, i)

    if st.session_state.question:
        _render_question(st.session_state.question)
else:
    st.markdown(
        '<div class="dm-hero"><h1>Dr. Mundo 🩺</h1>'
        "<p>Drop a photo of your doctor's request below and I'll tell you what to "
        "prepare, after PhilHealth and your HMO.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, q in enumerate(SAMPLES):
        if cols[i % 2].button(q, key=f"s{i}", use_container_width=True):
            st.session_state.pending_prompt = q
            st.rerun()

placeholder = ("Answer above, or type it here…" if st.session_state.question
               else "Ask about a price, or drop your request slip here…")
submitted = st.chat_input(placeholder, accept_file=True,
                          file_type=["png", "jpg", "jpeg", "webp"])

pending = st.session_state.pop("pending_prompt", None)

if submitted is not None:
    files = getattr(submitted, "files", None) or []
    text = (getattr(submitted, "text", None) or "").strip()
    if files:
        _handle_slip(files[0])
    elif text:
        _handle_text(text)
elif pending:
    _handle_text(pending)
