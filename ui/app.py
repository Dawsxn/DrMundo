"""Streamlit chat UI for Dr. Mundo — liquid-glass edition.

A thin client over the FastAPI `/ask` endpoint. It keeps a stable `session_id` in
`st.session_state` so the backend's short-term memory threads follow-up questions, then
renders: (1) the grounded natural-language answer, (2) a structured price/coverage
breakdown, and (3) a collapsible reasoning trace (Thought -> Action -> Observation).

The look is a teal "liquid glass" theme: an animated gradient-blob backdrop with frosted,
translucent panels (see `_inject_theme`). Quick-press sample prompts appear as welcome
cards (empty chat) and as sidebar chips (always).

Run the API first:  uvicorn api.main:app --reload
Then this UI:        streamlit run ui/app.py
"""

import os
import time
import uuid

import requests
import streamlit as st

API_URL = os.getenv("DR_MUNDO_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 90  # seconds; the agent may make several model calls per turn.

st.set_page_config(page_title="Dr. Mundo — PH Medical Cost Estimator",
                   page_icon="🩺", layout="centered", initial_sidebar_state="expanded")

# Curated sample prompts: (emoji, short label, full question). A deliberate mix of
# Path A (covered) and Path B (outpatient), English and Taglish.
SAMPLES = [
    ("🩺", "Appendectomy", "Magkano ang appendectomy sa Chong Hua?"),
    ("👶", "Normal delivery", "How much is a normal delivery?"),
    ("🧠", "CT scan (contrast)", "How much is a CT scan with contrast?"),
    ("🩻", "Chest X-ray", "Magkano ang xray ng baga?"),
    ("🦴", "Knee replacement", "How much is a total knee replacement?"),
    ("🧪", "Blood tests", "How much is a CBC and lipid profile?"),
]


# ----------------------------------------------------------------- liquid-glass theme
def _inject_theme() -> None:
    # NOTE: keep the <style> block free of BLANK LINES -- Streamlit's Markdown renderer
    # ends a raw-HTML block at the first blank line, which would leak CSS as page text.
    st.markdown(
        '<div class="lg-bg"><span class="lg-blob b1"></span>'
        '<span class="lg-blob b2"></span><span class="lg-blob b3"></span>'
        '<span class="lg-blob b4"></span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """<style>
:root{--glass:rgba(255,255,255,0.55);--glass-strong:rgba(255,255,255,0.72);--glass-border:rgba(255,255,255,0.65);--ink:#0e3a42;--accent:#06b6d4;--accent-deep:#0e7490;--shadow:0 8px 32px rgba(14,80,90,0.18);}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"],[data-testid="stMain"]{background:transparent !important;}
body{background:#dff3f4 !important;}
.lg-bg{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none;background:linear-gradient(160deg,#e9f8f9 0%,#d2f0f2 45%,#c2ebee 100%);}
.lg-blob{position:absolute;border-radius:50%;filter:blur(70px);opacity:.55;}
.lg-blob.b1{width:46vw;height:46vw;left:-8vw;top:-10vh;background:radial-gradient(circle at 30% 30%,#2dd4bf,transparent 70%);animation:drift1 24s ease-in-out infinite;}
.lg-blob.b2{width:40vw;height:40vw;right:-10vw;top:6vh;background:radial-gradient(circle at 30% 30%,#22d3ee,transparent 70%);animation:drift2 28s ease-in-out infinite;}
.lg-blob.b3{width:44vw;height:44vw;left:8vw;bottom:-16vh;background:radial-gradient(circle at 30% 30%,#6ee7b7,transparent 70%);animation:drift3 30s ease-in-out infinite;}
.lg-blob.b4{width:34vw;height:34vw;right:2vw;bottom:-8vh;background:radial-gradient(circle at 30% 30%,#38bdf8,transparent 70%);animation:drift1 26s ease-in-out infinite reverse;}
@keyframes drift1{0%,100%{transform:translate(0,0) scale(1);}50%{transform:translate(6vw,4vh) scale(1.12);}}
@keyframes drift2{0%,100%{transform:translate(0,0) scale(1);}50%{transform:translate(-5vw,6vh) scale(1.1);}}
@keyframes drift3{0%,100%{transform:translate(0,0) scale(1);}50%{transform:translate(4vw,-5vh) scale(1.15);}}
@media (prefers-reduced-motion:reduce){.lg-blob{animation:none !important;}}
[data-testid="stMain"],[data-testid="stSidebar"],[data-testid="stHeader"]{position:relative;z-index:1;}
[data-testid="stSidebar"],[data-testid="stChatMessage"],[data-testid="stExpander"] details,[data-testid="stAlert"],[data-testid="stTable"],div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--glass) !important;-webkit-backdrop-filter:blur(18px) saturate(160%);backdrop-filter:blur(18px) saturate(160%);border:1px solid var(--glass-border) !important;border-radius:18px !important;box-shadow:var(--shadow);}
[data-testid="stSidebar"]{border-radius:0 22px 22px 0 !important;}
[data-testid="stChatMessage"]{padding:14px 16px !important;margin-bottom:10px;}
[data-testid="stExpander"] details{box-shadow:none;}
[data-testid="stMetric"]{background:var(--glass-strong);border:1px solid var(--glass-border);border-radius:14px;padding:10px 12px;-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);box-shadow:0 4px 18px rgba(14,80,90,0.10);}
[data-testid="stMetricValue"]{color:var(--accent-deep) !important;font-weight:700;}
.stApp,[data-testid="stMarkdownContainer"],p,li,label,h1,h2,h3,h4{color:var(--ink);}
h1,h2,h3{letter-spacing:-0.01em;}
[data-testid="stChatInput"]{background:var(--glass-strong) !important;-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);border:1px solid var(--glass-border) !important;border-radius:16px !important;box-shadow:var(--shadow);}
[data-testid="stChatInput"] textarea{color:var(--ink) !important;}
.stButton > button{background:rgba(6,182,212,0.10) !important;border:1px solid rgba(6,182,212,0.30) !important;color:var(--accent-deep) !important;border-radius:14px !important;font-weight:600;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);text-align:left;transition:all .18s ease;}
.stButton > button:hover{background:rgba(6,182,212,0.20) !important;border-color:rgba(6,182,212,0.55) !important;box-shadow:0 0 0 1px rgba(6,182,212,.35),0 8px 22px rgba(6,182,212,.28);transform:translateY(-1px);}
[data-testid="stAlert"]{color:var(--ink) !important;}
.lg-hero{text-align:center;padding:6px 0 2px;}
.lg-hero .badge{display:inline-block;font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-deep);background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.28);padding:4px 12px;border-radius:999px;margin-bottom:10px;}
.lg-hero h1{margin:.1rem 0 .2rem;font-size:2.1rem;}
.lg-hero p{color:#2b6570;margin:.1rem 0 0;}
.lg-cards-label{text-align:center;color:#2b6570;font-size:.9rem;margin:14px 0 6px;}
</style>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------- session state
def _init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex
    if "messages" not in st.session_state:
        # Each item: {"role": "user"|"assistant", "text": str, "meta": dict|None}
        st.session_state.messages = []


def _new_chat() -> None:
    try:
        requests.post(f"{API_URL}/reset",
                      json={"session_id": st.session_state.session_id},
                      timeout=10)
    except requests.RequestException:
        pass  # a failed reset is harmless; we rotate the id locally anyway.
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []


# ----------------------------------------------------------------- rendering
def _peso(v) -> str:
    return f"₱{v:,.0f}" if v is not None else "n/a"


def _render_breakdown(answer: dict) -> None:
    """Structured price/coverage panel built from the grounded Answer fields."""
    if answer.get("status") != "answered" or not answer.get("path"):
        return

    path = answer["path"]
    with st.container(border=True):
        title = answer.get("procedure_or_service") or "Result"
        scope = answer.get("hospital")
        st.markdown(f"**{title}**" + (f" — {scope}" if scope else ""))

        if answer.get("price_low") is not None:
            cols = st.columns(3)
            cols[0].metric("Price range (low)", _peso(answer.get("price_low")))
            cols[1].metric("Price range (high)", _peso(answer.get("price_high")))
            if path == "covered":
                cols[2].metric("PhilHealth case rate", _peso(answer.get("case_rate")))
        elif path == "covered":
            st.metric("PhilHealth case rate", _peso(answer.get("case_rate")))
            st.caption("No hospital price is on file for this procedure yet.")

        if path == "covered" and answer.get("price_low") is not None:
            if answer.get("fully_covered"):
                st.success("PhilHealth may fully cover this "
                           "(case rate meets or exceeds the price range).")
            else:
                lo, hi = answer.get("oop_low"), answer.get("oop_high")
                st.info(f"Estimated out-of-pocket: {_peso(lo)} – {_peso(hi)}")
        elif path == "outpatient":
            st.warning("Not covered by PhilHealth (no case rate or out-of-pocket).")

        hospitals = answer.get("hospitals") or []
        if hospitals and not answer.get("hospital"):
            st.caption("Per hospital:")
            st.table([
                {
                    "Hospital": h.get("hospital"),
                    "City": h.get("city") or "",
                    "Low": _peso(h.get("price_low")),
                    "High": _peso(h.get("price_high")),
                }
                for h in hospitals
            ])

        if answer.get("as_of"):
            st.caption(f"As of {answer['as_of']}.")


def _render_trace(trace: list[dict]) -> None:
    if not trace:
        return
    with st.expander(f"🔎 Reasoning trace ({len(trace)} step(s))"):
        for i, step in enumerate(trace, 1):
            st.markdown(f"**Step {i} — Action:** `{step.get('action')}`")
            if step.get("thought"):
                st.markdown(f"*Thought:* {step['thought']}")
            if step.get("action_input"):
                st.markdown("*Action input:*")
                st.json(step["action_input"], expanded=False)
            if step.get("observation"):
                st.markdown("*Observation:*")
                st.json(step["observation"], expanded=False)


def _render_meta(meta: dict) -> None:
    bits = []
    if meta.get("category") and meta["category"] != "cost":
        bits.append(f"category: `{meta['category']}`")
    if meta.get("pii_found"):
        bits.append(f"PII redacted: {', '.join(meta['pii_found'])}")
    if meta.get("latency_ms"):
        bits.append(f"{meta['latency_ms']} ms")
    if meta.get("total_tokens"):
        bits.append(f"{meta['total_tokens']:,} tokens")
    if meta.get("estimated_cost_usd"):
        bits.append(f"${meta['estimated_cost_usd']:.4f}")
    if meta.get("prompt_version"):
        bits.append(f"prompt: {meta['prompt_version']}")
    report = meta.get("output_report") or {}
    if report.get("replaced"):
        bits.append("⚠️ ungrounded prose replaced")
    if bits:
        st.caption(" · ".join(bits))


def _stream_text(text: str):
    """Typewriter effect so the answer appears to stream in (the API returns it whole)."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.012)


def _process_turn(prompt: str) -> None:
    """Send one question to the API and render the answer (used by both the chat box
    and the quick-press sample prompts)."""
    st.session_state.messages.append({"role": "user", "text": prompt, "meta": None})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Checking the numbers…"):
                resp = requests.post(
                    f"{API_URL}/ask",
                    json={"question": prompt, "session_id": st.session_state.session_id},
                    timeout=REQUEST_TIMEOUT,
                )
        except requests.RequestException as exc:
            err = (f"⚠️ I couldn't reach the Dr. Mundo API at `{API_URL}`.\n\n"
                   f"Is it running? Start it with `uvicorn api.main:app --reload`.\n\n"
                   f"_Details: {exc}_")
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "text": err, "meta": None})
            return

        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer") or {}
            text = answer.get("answer_text", "_(no answer)_")
            st.write_stream(_stream_text(text))
            _render_breakdown(answer)
            _render_trace(data.get("trace") or [])
            _render_meta(data)
            st.session_state.messages.append(
                {"role": "assistant", "text": text, "meta": data}
            )
        elif resp.status_code == 422:
            msg = "⚠️ That question looks empty or malformed. Please try rephrasing."
            st.error(msg)
            st.session_state.messages.append({"role": "assistant", "text": msg, "meta": None})
        else:
            detail = ""
            try:
                detail = resp.json().get("detail", "")
            except ValueError:
                detail = resp.text[:200]
            msg = f"⚠️ Something went wrong (HTTP {resp.status_code}). _{detail}_"
            st.error(msg)
            st.session_state.messages.append({"role": "assistant", "text": msg, "meta": None})


def _render_welcome() -> str | None:
    """Hero + tappable sample cards, shown when the chat is empty. Returns a clicked
    question, or None."""
    st.markdown(
        '<div class="lg-hero">'
        '<span class="badge">Philippine Healthcare Cost Estimator</span>'
        '<h1>Dr. Mundo 🩺</h1>'
        '<p>Ask about the cost of a covered procedure or an outpatient service, '
        'in English or Taglish.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="lg-cards-label">Try one of these to get started</div>',
                unsafe_allow_html=True)
    clicked = None
    cols = st.columns(2)
    for i, (emoji, _label, question) in enumerate(SAMPLES):
        if cols[i % 2].button(f"{emoji}  {question}", key=f"card_{i}",
                              use_container_width=True):
            clicked = question
    return clicked


# ----------------------------------------------------------------- app
_inject_theme()
_init_state()

# A sample prompt clicked on a previous run (set + rerun) is picked up here so the
# welcome screen disappears cleanly before the answer renders.
pending = st.session_state.pop("pending_prompt", None)
clicked_q = None

with st.sidebar:
    st.header("Dr. Mundo 🩺")
    st.caption("Cost estimates for Philippine medical procedures & outpatient services.")
    st.button("🧹 New chat", on_click=_new_chat, use_container_width=True)

    st.divider()
    st.markdown("**Try asking**")
    for i, (emoji, label, question) in enumerate(SAMPLES):
        if st.button(f"{emoji}  {label}", key=f"chip_{i}", use_container_width=True):
            st.session_state.pending_prompt = question
            st.rerun()

    st.divider()
    st.caption(f"API: `{API_URL}`")
    st.caption(f"Session: `{st.session_state.session_id[:8]}…`")
    st.caption("Estimates only — not medical advice.")

# Main area: welcome cards when empty, otherwise the conversation.
if st.session_state.messages or pending:
    st.title("Dr. Mundo")
    st.caption("Ask about the cost of a covered procedure or an outpatient service. English or Taglish.")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])
            if msg["role"] == "assistant" and msg.get("meta"):
                meta = msg["meta"]
                _render_breakdown(meta.get("answer") or {})
                _render_trace(meta.get("trace") or [])
                _render_meta(meta)
else:
    card_q = _render_welcome()
    if card_q:
        st.session_state.pending_prompt = card_q
        st.rerun()

prompt = st.chat_input("Magtanong tungkol sa presyo…")

user_msg = prompt or pending or clicked_q
if user_msg:
    _process_turn(user_msg)
