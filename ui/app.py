"""Streamlit chat UI for Dr. Mundo.

One conversation. The patient drags a photo of their doctor's request into the chat box.
Dr. Mundo says what it read, then asks the remaining questions in plain language, one at
a time, and only shows the figure once intake is finished. The report then renders as a
PDF that can be read inline or downloaded.

Two things are deliberate about the layout:

  The uploaded photo is shown in the conversation and opens full size when clicked, so a
  patient can check that we read the right piece of paper before trusting a number that
  came off it.

  No price appears mid-intake. A half-answered estimate is the one most likely to be
  wrong in the direction that costs the patient money, so the summary names what was read
  and holds the total back until HMO, senior status and any planned operation are known.

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
                   page_icon="🩺", layout="centered", initial_sidebar_state="collapsed")

SAMPLES = [
    "Magkano ang tanggal apdo?",
    "How much is a lipid profile?",
    "Magkano ang CBC?",
    "Magkano ang creatinine?",
]


# ----------------------------------------------------------------- theme
def _inject_theme() -> None:
    # Plain white. Keep the block free of blank lines: Streamlit's Markdown renderer ends
    # a raw-HTML block at the first one, which would spill CSS onto the page as text.
    st.markdown(
        """<style>
:root{--ink:#111827;--mute:#6b7280;--line:#e5e7eb;--accent:#0e7490;}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"],[data-testid="stMain"]{background:#ffffff !important;}
[data-testid="stSidebar"]{background:#fafafa !important;border-right:1px solid var(--line);}
.stApp,[data-testid="stMarkdownContainer"],p,li,label,h1,h2,h3,h4{color:var(--ink);}
[data-testid="stChatMessage"]{background:transparent !important;border:0 !important;box-shadow:none !important;padding:6px 0 !important;}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p{margin-bottom:.4rem;}
[data-testid="stChatInput"]{border:1px solid var(--line) !important;border-radius:12px !important;background:#fff !important;box-shadow:0 1px 2px rgba(0,0,0,.04);}
.stButton > button{border:1px solid var(--line) !important;background:#fff !important;color:var(--ink) !important;border-radius:10px !important;font-weight:500;text-align:left;}
.stButton > button:hover{border-color:var(--accent) !important;color:var(--accent) !important;}
[data-testid="stExpander"] details{border:1px solid var(--line) !important;border-radius:10px !important;background:#fff !important;box-shadow:none !important;}
[data-testid="stTable"]{border:1px solid var(--line);border-radius:10px;}
.dm-hero{text-align:center;padding:34px 0 10px;}
.dm-hero h1{font-size:2rem;margin:.2rem 0;}
.dm-hero p{color:var(--mute);margin:0;}
.dm-amount{font-size:2rem;font-weight:700;line-height:1.15;margin:.1rem 0 .6rem;}
.dm-amount-label{font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--mute);}
.dm-note{color:var(--mute);font-size:.84rem;}
</style>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------- state
def _init_state() -> None:
    st.session_state.setdefault("session_id", uuid.uuid4().hex)
    st.session_state.setdefault("messages", [])      # {role, text, meta, image}
    st.session_state.setdefault("has_estimate", False)   # intake finished
    st.session_state.setdefault("has_slip", False)       # a slip is in play


def _new_chat() -> None:
    try:
        requests.post(f"{API_URL}/reset",
                      json={"session_id": st.session_state.session_id}, timeout=10)
    except requests.RequestException:
        pass
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []
    st.session_state.has_estimate = False
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


def _render_slip_thumbnail(image_bytes: bytes, key: str) -> None:
    """The photo, in the conversation, openable full size.

    Worth the space: it lets a patient confirm we read the right piece of paper before
    they trust a number that came off it.
    """
    cols = st.columns([1, 3])
    with cols[0]:
        st.image(image_bytes, use_container_width=True)
    with cols[1]:
        st.caption("Your uploaded request.")
        if st.button("View full size", key=f"view_{key}", use_container_width=False):
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

    # These buckets never collapse away: an item quietly missing from a report is how an
    # understated bill becomes invisible.
    for key, title, note in (
        ("unpriced", "Not priced",
         "MMC publishes no price for these, so they are **not** in the total."),
        ("needs_confirmation", "Please confirm",
         "I need a little more detail before I can price these."),
        ("cancelled", "Crossed out by your doctor",
         "Not ordered, so **not** charged."),
    ):
        items = budget.get(key) or []
        if items:
            with st.expander(f"{title} ({len(items)})", expanded=True):
                st.caption(note)
                for it in items:
                    st.markdown(f"- {it.get('normalized') or it.get('raw_text')}")

    for caveat in budget.get("caveats") or []:
        st.markdown(f'<div class="dm-note">{caveat}</div>', unsafe_allow_html=True)


def _fetch_pdf() -> bytes | None:
    """Pull the PDF for this session. Called once, when the report is finished."""
    try:
        resp = requests.get(f"{API_URL}/report.pdf",
                            params={"session_id": st.session_state.session_id},
                            timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return None
    return resp.content if resp.status_code == 200 else None


def _render_pdf(payload: bytes, key: str) -> None:
    """Show the report inline and offer it as a download.

    Rendered in the conversation rather than the sidebar: Streamlit draws the sidebar
    BEFORE the main area, so anything gated on state set while handling a turn will not
    appear until some later rerun. That is exactly how the refine controls went missing.
    """
    if not payload:
        return
    st.download_button("Download the PDF", payload, key=f"dl_{key}",
                       file_name="dr-mundo-estimate.pdf", mime="application/pdf",
                       use_container_width=True)
    try:
        st.pdf(payload, height=620)
    except Exception:
        # Older Streamlit without st.pdf: embed it instead of dropping the preview.
        b64 = base64.b64encode(payload).decode()
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="620" '
            f'style="border:1px solid #e5e7eb;border-radius:10px"></iframe>',
            unsafe_allow_html=True,
        )


def _render_message(msg: dict, index: int) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("image"):
            _render_slip_thumbnail(msg["image"], key=f"m{index}")
        if msg.get("text"):
            st.markdown(msg["text"])
        meta = msg.get("meta")
        if msg["role"] == "assistant" and meta:
            answer = meta.get("answer") or {}
            if answer.get("budget"):
                _render_budget(answer)
                if msg.get("pdf"):
                    _render_pdf(msg["pdf"], key=f"m{index}")


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


def _handle_slip(file) -> None:
    payload = file.getvalue()
    st.session_state.messages.append(
        {"role": "user", "text": "", "meta": None, "image": payload})
    _render_message(st.session_state.messages[-1], len(st.session_state.messages) - 1)

    with st.chat_message("assistant"), st.spinner("Reading your request slip…"):
        data = _post("/ask-slip",
                     files={"file": (file.name, payload, file.type or "image/png")},
                     data={"session_id": st.session_state.session_id})
        if data is None:
            return
        answer = data.get("answer") or {}
        st.markdown(answer.get("answer_text", ""))
        _render_budget(answer)
        st.session_state.has_slip = True
        st.session_state.has_estimate = bool(answer.get("budget"))
        pdf = _fetch_pdf() if answer.get("budget") else None
        if pdf:
            _render_pdf(pdf, key="live_slip")
        st.session_state.messages.append(
            {"role": "assistant", "text": answer.get("answer_text", ""),
             "meta": data, "image": None, "pdf": pdf})


def _handle_text(text: str) -> None:
    st.session_state.messages.append(
        {"role": "user", "text": text, "meta": None, "image": None})
    with st.chat_message("user"):
        st.markdown(text)

    # With a slip in play, plain text is an answer to the question we just asked.
    # Without one, it is an ordinary cost question for the v1 path.
    endpoint = "/converse" if st.session_state.has_slip else "/ask"
    body = ({"text": text, "session_id": st.session_state.session_id}
            if endpoint == "/converse"
            else {"question": text, "session_id": st.session_state.session_id})

    with st.chat_message("assistant"), st.spinner("Checking the numbers…"):
        data = _post(endpoint, json=body)
        if data is None:
            return
        answer = data.get("answer") or {}
        st.markdown(answer.get("answer_text", ""))
        _render_budget(answer)
        pdf = None
        if answer.get("budget"):
            st.session_state.has_estimate = True
            pdf = _fetch_pdf()
            if pdf:
                _render_pdf(pdf, key="live_text")
        st.session_state.messages.append(
            {"role": "assistant", "text": answer.get("answer_text", ""),
             "meta": data, "image": None, "pdf": pdf})


# ----------------------------------------------------------------- app
_inject_theme()
_init_state()

with st.sidebar:
    st.markdown("### Dr. Mundo 🩺")
    st.caption("Cost estimates for Makati Medical Center, grounded in published prices.")
    st.button("New chat", on_click=_new_chat, use_container_width=True)
    st.divider()
    st.caption(f"API: `{API_URL}`")
    st.caption("Estimates only. Not medical advice.")

if not st.session_state.messages:
    st.markdown(
        '<div class="dm-hero"><h1>Dr. Mundo 🩺</h1>'
        "<p>Drag a photo of your doctor's request into the box below, "
        "and I'll tell you what to prepare.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, q in enumerate(SAMPLES):
        if cols[i % 2].button(q, key=f"s{i}", use_container_width=True):
            st.session_state.pending_prompt = q
            st.rerun()
else:
    for i, msg in enumerate(st.session_state.messages):
        _render_message(msg, i)

submitted = st.chat_input(
    "Ask about a price, or drop your request slip here…",
    accept_file=True,
    file_type=["png", "jpg", "jpeg", "webp"],
)

pending = st.session_state.pop("pending_prompt", None)

if submitted is not None:
    files = getattr(submitted, "files", None) or []
    text = (getattr(submitted, "text", None) or "").strip()
    if files:
        _handle_slip(files[0])
        if text:
            _handle_text(text)
    elif text:
        _handle_text(text)
elif pending:
    _handle_text(pending)
