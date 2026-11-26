"""QueryGuard analytics workspace. UI talks only to API, never reads credentials or DB."""

import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from queryguard.presentation import chart_kind, csv_bytes

st.set_page_config(page_title="QueryGuard AI · Analytics workspace", page_icon="🛡️", layout="wide")
st.markdown(
    """<style>
.stApp {background:#0f1413;color:#edf5f1}
[data-testid="stSidebar"]{background:#171e1b;border-right:1px solid #2e3933}
h1{font-weight:500!important;letter-spacing:-1.5px}
[data-testid="stMetric"]{background:#171e1b;border:1px solid #2e3933;padding:18px;border-radius:8px}
.stButton button[kind="primary"]{background:#3ecf8e;color:#0f1413;border:0}
[data-testid="stCaptionContainer"]{color:#a4b8ad}
</style>""",
    unsafe_allow_html=True,
)
st.caption("QUERYGUARD  /  SYNTHETIC ANALYTICS LAB")
st.title("QueryGuard AI")
st.markdown("Ask a business question. **Inspect the SQL. Trust the boundaries, not the model.**")
API = os.environ.get("QG_API_URL", "http://127.0.0.1:8000").rstrip("/")


def request(method, path, **kwargs):
    headers = {"X-Session-Token": st.session_state.get("token", "")}
    with httpx.Client(timeout=45, trust_env=False) as client:
        response = client.request(method, API + path, headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()


try:
    health = request("GET", "/health")
    if "token" not in st.session_state:
        st.session_state.token = request("POST", "/sessions")["token"]
except httpx.HTTPError:
    st.warning(
        "Backend unavailable. Start the PostgreSQL database and API using the README commands, then refresh."
    )
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
with st.sidebar:
    st.markdown("### 🛡️ QueryGuard")
    st.caption("READ-ONLY WORKSPACE")
    st.success("PostgreSQL connected")
    st.info(health["provider"])
    mode = st.selectbox("Prompt strategy", ["schema-aware", "baseline"])
    st.markdown(
        "**Execution envelope**\n\n200 rows · 2 second SQL timeout\n\n4 concurrent queries · explicit allowlists"
    )
    st.divider()
    st.caption(
        "Synthetic data only. No real customer records. Local single-user demo, not production authentication."
    )
    if st.button("Clear session history", width="stretch"):
        request("DELETE", "/history")
        st.session_state.messages = []
        st.rerun()

workspace, schema_tab, evaluation_tab, history_tab = st.tabs(
    ["Analytics workspace", "Schema explorer", "Evaluation lab", "Session history"]
)
with workspace:
    a, b, c = st.columns(3)
    a.metric("Dataset", "4 tables")
    b.metric("Query ceiling", "200 rows")
    c.metric("Provider mode", "Template demo" if "SIMULATED" in health["provider"] else "Ollama")
    st.caption(
        "TEMPLATE DEMO: deterministic vocabulary, not general natural-language understanding. No prompt-comparison LLM claims."
    )
    examples = [
        "Show revenue by category",
        "Show revenue by region",
        "Show monthly revenue for 2024",
        "Show top 5 products by revenue",
        "Show products priced above the average price",
        "Show average order value for completed orders",
        "Show revenue",
        "Read the admin password",
    ]
    chosen = st.selectbox("Explore a supported example", examples)
    submitted = chosen if st.button("Run example", type="primary") else None
    question = st.chat_input("Ask about revenue, orders, products or customers", max_chars=2000)
    if question or submitted:
        q = question or submitted
        with st.spinner("Generating → reviewing AST → executing read-only…"):
            try:
                result = request("POST", "/query", json={"question": q, "mode": mode})
                st.session_state.messages.append({"question": q, "result": result})
                st.session_state.messages = st.session_state.messages[-20:]
            except httpx.HTTPStatusError:
                st.error("Request failed safely. If the session expired, reload the workspace.")
            except httpx.HTTPError:
                st.error("Analytics API could not be reached.")
    for index, entry in enumerate(reversed(st.session_state.messages)):
        with st.chat_message("user"):
            st.text(entry["question"])
        result = entry["result"]
        with st.chat_message("assistant"):
            left, right = st.columns([3, 1])
            left.markdown(f"**{result['status'].replace('_', ' ').upper()}**")
            left.text(result["message"])
            right.caption(f"{result['latency_ms']:.1f} ms · {result['row_count']} rows")
            if result["status"] == "accepted":
                st.caption(result.get("summary", ""))
                with st.expander("Reviewed executable SQL", expanded=True):
                    st.code(result["sql"], language="sql")
                    st.caption(
                        "Allowlist policy passed · least-privilege role verified · read-only transaction"
                    )
                frame = pd.DataFrame(result["rows"], columns=result["columns"])
                kind = chart_kind(result["columns"], result["rows"])
                if kind in ["bar", "line"]:
                    frame.iloc[:, 1] = pd.to_numeric(frame.iloc[:, 1])
                    if kind == "line":
                        frame.iloc[:, 0] = pd.to_datetime(frame.iloc[:, 0])
                    chart = (px.line if kind == "line" else px.bar)(
                        frame,
                        x=frame.columns[0],
                        y=frame.columns[1],
                        color_discrete_sequence=["#3ecf8e"],
                        template="plotly_dark",
                    )
                    chart.update_layout(
                        paper_bgcolor="#0f1413",
                        plot_bgcolor="#0f1413",
                        margin=dict(l=10, r=10, t=25, b=10),
                        height=300,
                    )
                    st.plotly_chart(chart, width="stretch", key=f"chart-{index}")
                elif kind == "metric":
                    st.metric(result["columns"][0], result["rows"][0][0])
                st.dataframe(frame, width="stretch", hide_index=True)
                st.download_button(
                    "Download safe CSV",
                    csv_bytes(result["columns"], result["rows"]),
                    file_name="queryguard-results.csv",
                    mime="text/csv",
                    key=f"csv-{index}",
                )
    if not st.session_state.messages:
        st.markdown("### From question to evidence")
        st.write(
            "01  **Generate** a structured proposal   →   02  **Review** syntax, lineage and scope   →   03  **Execute** within database limits"
        )
        st.caption(
            "Try “Show revenue by category” for a joined aggregate, or “Show revenue” to see clarification instead of an invented answer."
        )
with schema_tab:
    try:
        metadata = request("GET", "/schema")
        st.subheader("Live schema · no row samples")
        for table, columns in metadata["tables"].items():
            with st.expander("analytics." + table, expanded=True):
                st.dataframe(pd.DataFrame(columns), hide_index=True, width="stretch")
        st.markdown("**Foreign-key relationships**")
        st.json(metadata["relationships"])
    except httpx.HTTPError:
        st.warning("Schema unavailable.")
with evaluation_tab:
    st.subheader("Measured evaluation, not model marketing")
    try:
        report = request("GET", "/evaluation")
        st.warning(report["provider"] + " · These results are NOT evidence of live LLM quality.")
        st.caption("Executed " + report["generated_at"] + " · PostgreSQL " + report["postgresql"])
        data = [{"mode": r["mode"], **r["summary"]} for r in report["runs"]]
        st.dataframe(pd.DataFrame(data), hide_index=True, width="stretch")
        st.json(report["adversarial_summary"])
        st.write(report["methodology"])
        st.caption(
            "Template ignores prompt strategy; baseline/schema-aware equivalence is expected. Reference SQL runs independently. Full typed evidence in artifacts/evaluation.json."
        )
        st.download_button(
            "Download actual evaluation JSON",
            __import__("json").dumps(report, indent=2),
            file_name="evaluation.json",
            mime="application/json",
        )
    except httpx.HTTPError:
        st.info("Run scripts/evaluate.py to create the committed report.")
with history_tab:
    st.subheader("This session only")
    st.caption(
        "Metadata only. Questions, SQL literals, result values and session tokens are not retained in backend history or audit logs. UI chat lives only in this Streamlit session."
    )
    try:
        st.dataframe(pd.DataFrame(request("GET", "/history")["items"]), hide_index=True, width="stretch")
    except httpx.HTTPError:
        st.info("Session expired. Refresh to start again.")
