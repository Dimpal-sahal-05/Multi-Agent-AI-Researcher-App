import re
import io
import json
import threading
import queue
import contextlib
import streamlit as st
from datetime import datetime

from pipeline import run_research_pipeline

st.set_page_config(page_title="Multi Agent AI Researcher", page_icon="🖋️", layout="wide")

# ---------------------------------------------------------------------------
# Design tokens & global styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
    :root {
        --ink: #141C22;
        --ink-soft: #1C2730;
        --ink-line: #354A57;
        --ink-text: #F4F0E6;
        --ink-text-dim: #C2D1D6;
        --paper: #F2ECDA;
        --paper-text: #241F16;
        --brass: #D4A373;
        --brass-dark: #A98467;
        --teal: #52B788;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--ink);
        color: var(--ink-text);
        font-family: 'IBM Plex Sans', sans-serif;
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { display: none; }

    .main .block-container {
        max-width: 780px;
        padding-top: 3rem;
    }

    /* ---------- Masthead & Hero ---------- */
    .masthead {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--ink-line);
        padding-bottom: 0.8rem;
        margin-bottom: 2rem;
    }
    .masthead-mark {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: var(--brass);
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .masthead-meta {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--ink-text-dim);
    }
    .hero-title {
        font-family: 'Fraunces', serif;
        font-weight: 500;
        font-size: 2.6rem;
        line-height: 1.1;
        color: var(--ink-text);
        margin: 0 0 0.6rem 0;
    }
    .hero-sub {
        font-size: 1.02rem;
        color: var(--ink-text-dim);
        max-width: 54ch;
        line-height: 1.55;
        margin-bottom: 2rem;
    }

    /* ---------- Agent Grid Boxes ---------- */
    .roster-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
        color: var(--brass);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 2.5rem 0 1rem 0;
        font-weight: 600;
    }
    .agent-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 2.5rem;
    }
    .agent-box {
        background: #1E2B36;
        border: 1.5px solid #415A6C;
        border-radius: 6px;
        padding: 0.9rem 1rem;
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: #FFFFFF;
        font-weight: 500;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }

    /* ---------- Inputs ---------- */
    [data-testid="stTextInput"] label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: var(--brass);
        font-weight: 600;
    }
    [data-testid="stTextInput"] input {
        background: #1B2631;
        border: none;
        border-bottom: 2px solid var(--ink-line);
        border-radius: 4px;
        color: #FFFFFF;
        font-size: 1.05rem;
        padding: 0.7rem 0.5rem;
    }
    [data-testid="stTextInput"] input:focus {
        border-bottom: 2px solid var(--brass);
        box-shadow: none;
    }

    [data-testid="stFormSubmitButton"] button {
        background: var(--brass);
        color: #1A130B;
        border: none;
        border-radius: 4px;
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 700;
        padding: 0.6rem 1.5rem;
        margin-top: 0.8rem;
        width: 100%;
        font-size: 1rem;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        background: var(--brass-dark);
        color: #FFFFFF;
    }

    /* ---------- Sidebar Pipeline Rail & History ---------- */
    [data-testid="stSidebar"] {
        background: #17212B;
        border-right: 1px solid var(--ink-line);
    }
    .rail-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: var(--brass);
        margin-bottom: 1.2rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .rail-step {
        display: flex;
        align-items: flex-start;
        gap: 0.8rem;
        position: relative;
        padding-bottom: 1.8rem;
    }
    .rail-dot {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 2px solid #415A6C;
        background: #1B2631;
    }
    .rail-dot.done { background: var(--teal); border-color: var(--teal); }
    .rail-dot.running { border-color: var(--brass); background: var(--brass); }
    .rail-label { font-size: 0.9rem; color: #D8EEF3; font-weight: 500; }
    .rail-step.done .rail-label { color: #FFFFFF; font-weight: 600; }
    .rail-step.running .rail-label { color: var(--brass); font-weight: 700; }

    /* ---------- Log & Paper Panels ---------- */
    .log-panel {
        background: #0B1014;
        border: 1px solid var(--ink-line);
        border-radius: 4px;
        padding: 1rem;
        max-height: 340px;
        overflow-y: auto;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #76C893;
    }
    .paper-panel {
        background: var(--paper);
        color: var(--paper-text);
        border-radius: 4px;
        padding: 2rem;
    }
    .score-num {
        font-family: 'Fraunces', serif;
        font-size: 3.2rem;
        color: var(--brass);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Pipeline metadata
STAGES = [
    "Research agent — gathering methodologies & facts",
    "arXiv agent — finding academic preprints",
    "PDF reader — extracting equations & proofs",
    "Web scraper — deep-reading top sources",
    "Writer — drafting the report",
    "Critic — scoring & reviewing",
]
STEP_PATTERNS = [re.compile(rf"step\s*{n}\b", re.I) for n in range(1, 7)]

def render_rail(status: list):
    html = ['<div class="rail-title">PIPELINE WORKFLOW</div>']
    for i, label in enumerate(STAGES):
        state = status[i]
        html.append(
            f'<div class="rail-step {state}">'
            f'<div class="rail-dot {state}"></div>'
            f'<div class="rail-label">{label}</div>'
            f'</div>'
        )
    return "".join(html)

def update_status_from_log(buffer: str, status: list):
    for i, pat in enumerate(STEP_PATTERNS):
        if pat.search(buffer):
            for j in range(i):
                if status[j] != "done":
                    status[j] = "done"
            if status[i] != "done":
                status[i] = "running"
    return status

class QueueWriter(io.TextIOBase):
    def __init__(self, q):
        self.q = q
    def write(self, s):
        if s:
            self.q.put(s)
        return len(s)
    def flush(self):
        pass

def _run_pipeline_in_thread(topic, log_queue, result_box):
    writer = QueueWriter(log_queue)
    try:
        with contextlib.redirect_stdout(writer):
            state = run_research_pipeline(topic)
        result_box["state"] = state
    except Exception as e:
        result_box["error"] = e
    finally:
        log_queue.put(None)

# Session state initialization
for key, default in [
    ("running", False),
    ("final_state", None),
    ("log_text", ""),
    ("status", ["pending"] * 6),
    ("search_history", []), # List of dicts: {"topic": ..., "state": ..., "time": ...}
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Sidebar (Pipeline Rail + Clickable History)
# ---------------------------------------------------------------------------
with st.sidebar:
    rail_placeholder = st.empty()
    rail_placeholder.markdown(render_rail(st.session_state.status), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<div class="rail-title">📜 SEARCH HISTORY</div>', unsafe_allow_html=True)
    
    if not st.session_state.search_history:
        st.markdown('<div style="color: #8A9BA8; font-size: 0.8rem; font-family: monospace;">No previous searches yet.</div>', unsafe_allow_html=True)
    else:
        for idx, item in enumerate(reversed(st.session_state.search_history)):
            btn_label = f"📌 {item['time']} — {item['topic'][:22]}..."
            if st.button(btn_label, key=f"hist_btn_{idx}", use_container_width=True):
                st.session_state.final_state = item["state"]
                st.session_state.status = ["done"] * 6
                st.rerun()

# ---------------------------------------------------------------------------
# Hero Header Section
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="masthead">
        <div class="masthead-mark">The Research Agent</div>
        <div class="masthead-meta">Gemini · LangChain · Tavily · arXiv</div>
    </div>

    <div class="hero-title">AI Deep Researcher Agent</div>
    <div class="hero-sub">
        Six agents work a topic in sequence — web search, arXiv, PDF extraction,
        deep scraping, drafting, and peer review — and hand back a structured,
        sourced report with a critic's score.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("topic_form"):
    topic = st.text_input("Topic", placeholder="e.g. Retrieval-augmented generation for scientific literature review")
    submitted = st.form_submit_button("Begin research", disabled=st.session_state.running)

# ---------------------------------------------------------------------------
# Active Agent Roster
# ---------------------------------------------------------------------------
agents_list = [
    "01. Research Agent",
    "02. arXiv Agent",
    "03. PDF Reader",
    "04. Web Scraper",
    "05. Writer Chain",
    "06. Critic Reviewer"
]
agents_html = "".join([f'<div class="agent-box">{agent}</div>' for agent in agents_list])

st.markdown(
    f"""
    <div class="roster-title">Active Agent Roster</div>
    <div class="agent-grid">
        {agents_html}
    </div>
    """,
    unsafe_allow_html=True,
)

if submitted and topic.strip():
    st.session_state.running = True
    st.session_state.final_state = None
    st.session_state.log_text = ""
    st.session_state.status = ["pending"] * 6
    st.rerun()

# ---------------------------------------------------------------------------
# Execution + streaming logic
# ---------------------------------------------------------------------------
if st.session_state.running and st.session_state.final_state is None:
    log_queue = queue.Queue()
    result_box = {}

    thread = threading.Thread(target=_run_pipeline_in_thread, args=(topic, log_queue, result_box), daemon=True)
    thread.start()

    log_placeholder = st.empty()
    log_buffer = ""

    while True:
        chunk = log_queue.get()
        if chunk is None:
            break
        log_buffer += chunk
        update_status_from_log(log_buffer, st.session_state.status)
        rail_placeholder.markdown(render_rail(st.session_state.status), unsafe_allow_html=True)
        log_placeholder.markdown(f'<div class="log-panel">{log_buffer}</div>', unsafe_allow_html=True)

    thread.join()
    st.session_state.log_text = log_buffer

    if "error" in result_box:
        st.session_state.running = False
        st.error(f"Pipeline failed: {result_box['error']}")
    else:
        st.session_state.status = ["done"] * 6
        rail_placeholder.markdown(render_rail(st.session_state.status), unsafe_allow_html=True)
        final_state_data = result_box.get("state")
        st.session_state.final_state = final_state_data
        
        # Save to History with Timestamp
        timestamp_str = datetime.now().strftime("%m-%d %H:%M")
        # Check if topic already exists to avoid duplicates
        st.session_state.search_history.append({
            "topic": topic.strip(),
            "state": final_state_data,
            "time": timestamp_str
        })
        
        st.session_state.running = False
        st.rerun()

elif st.session_state.log_text and not st.session_state.running:
    with st.expander("Agent log"):
        st.markdown(f'<div class="log-panel">{st.session_state.log_text}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Results Tabs Display & Download Options
# ---------------------------------------------------------------------------
state = st.session_state.final_state
if state:
    st.markdown("### 📥 Download Options")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Report (.md)", 
            data=state.get("report", ""), 
            file_name="research_report.md", 
            mime="text/markdown",
            use_container_width=True
        )
    with col2:
        # Full package backup JSON export
        json_data = json.dumps(state, indent=4, default=str)
        st.download_button(
            "💾 Download All Data Backup (.json)", 
            data=json_data, 
            file_name="complete_research_data.json", 
            mime="application/json",
            use_container_width=True
        )

    st.markdown("---")
    tabs = st.tabs(["Report", "Critique", "Research", "arXiv", "PDF extract", "Scraped web"])

    with tabs[0]:
        st.markdown(f'<div class="paper-panel">{state.get("report", "No report generated.")}</div>', unsafe_allow_html=True)

    with tabs[1]:
        critique = state.get("critique", "No critique generated.")
        score_match = re.search(r"score:\s*([\d.]+)\s*/\s*10", critique, re.I)
        if score_match:
            st.markdown(
                f'<div style="display:flex; align-items:baseline; gap:0.9rem; margin-bottom:1.2rem;">'
                f'<div class="score-num">{score_match.group(1)}</div>'
                f'<div style="font-family:monospace; font-size:0.78rem; color:#9AA7AC;">OUT OF 10 — CRITIC SCORE</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<div class="paper-panel">{critique}</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown(f'<div class="paper-panel">{state.get("research_results", "No research results.")}</div>', unsafe_allow_html=True)

    with tabs[3]:
        st.markdown(f'<div class="paper-panel">{state.get("arxiv_results", "No arXiv results.")}</div>', unsafe_allow_html=True)

    with tabs[4]:
        st.markdown(f'<div class="paper-panel">{state.get("pdf_content", "No PDF content extracted.")}</div>', unsafe_allow_html=True)

    with tabs[5]:
        st.markdown(f'<div class="paper-panel">{state.get("scraped_content", "No scraped content.")}</div>', unsafe_allow_html=True)
        
    rail_placeholder.markdown(render_rail(st.session_state.status), unsafe_allow_html=True)