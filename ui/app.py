"""Streamlit chat UI for Dr. Mundo.

A thin client over the FastAPI `/ask` endpoint. It keeps a stable `session_id` in
`st.session_state` so the backend's short-term memory threads follow-up questions, then
renders: (1) the grounded natural-language answer, (2) a structured price/coverage
breakdown, and (3) a collapsible reasoning trace (Thought -> Action -> Observation).

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

st.set_page_config(page_title="Dr. Mundo — PH Medical Cost Estimator", page_icon="🩺")


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


# ----------------------------------------------------------------- app
_init_state()

with st.sidebar:
    st.header("Dr. Mundo 🩺")
    st.caption("Cost estimates for Philippine medical procedures & outpatient services.")
    st.button("🧹 New chat", on_click=_new_chat, use_container_width=True)
    st.divider()
    st.caption(f"API: `{API_URL}`")
    st.caption(f"Session: `{st.session_state.session_id[:8]}…`")
    st.divider()
    st.caption(
        "Ask things like:\n\n"
        "- *Magkano ang appendectomy sa Chong Hua?*\n"
        "- *How much is a normal delivery?*\n"
        "- *CT scan with contrast price*\n\n"
        "Estimates only — not medical advice."
    )

st.title("Dr. Mundo")
st.caption("Ask about the cost of a covered procedure or an outpatient service. English or Taglish.")

# Replay history.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if msg["role"] == "assistant" and msg.get("meta"):
            meta = msg["meta"]
            _render_breakdown(meta.get("answer") or {})
            _render_trace(meta.get("trace") or [])
            _render_meta(meta)

# New turn.
if prompt := st.chat_input("Magtanong tungkol sa presyo…"):
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
        else:
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
