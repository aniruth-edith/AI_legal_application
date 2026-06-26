import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Judiciary AI", layout="wide",
                   page_icon="⚖️")

# ── Session state ─────────────────────────────────────────────────────────────

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None


# def api(method: str, path: str, **kwargs):
#     headers = {}
#     if st.session_state.token:
#         headers["Authorization"] = f"Bearer {st.session_state.token}"
#     resp = getattr(requests, method)(f"{API_BASE}{path}",
#                                     headers=headers, **kwargs)
#     return resp

def api(method: str, path: str, **kwargs):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    # Different timeouts for different operations
    if "timeout" not in kwargs:
        kwargs["timeout"] = 120  # 2 minutes default
    
    resp = getattr(requests, method)(
        f"{API_BASE}{path}",
        headers=headers,
        **kwargs
    )
    return resp


# ── Auth page ──────────────────────────────────────────────────────────────────

# def auth_page():
#     st.title("⚖️ Judiciary AI — Legal Analytics")
#     tab1, tab2 = st.tabs(["Login", "Register"])
#     with tab1:
#         u = st.text_input("Username", key="login_u")
#         p = st.text_input("Password", type="password", key="login_p")
#         if st.button("Login"):
#             r = api("post", "/auth/login",
#                     data={"username": u, "password": p})
#             if r.status_code == 200:
#                 st.session_state.token = r.json()["access_token"]
#                 st.session_state.user = u
#                 st.rerun()
#             else:
#                 st.error("Invalid credentials")
#     with tab2:
#         u2 = st.text_input("Username", key="reg_u")
#         p2 = st.text_input("Password", type="password", key="reg_p")
#         # if st.button("Register"):
#         #     r = api("post", "/auth/register",
#         #             json={"username": u2, "password": p2})
#         #     if r.status_code == 200:
#         #         st.session_state.token = r.json()["access_token"]
#         #         st.session_state.user = u2
#         #         st.rerun()
#         #     else:
#         #         st.error(r.json().get("detail", "Error"))
#         # In auth_page(), replace the register button block with:
#         if st.button("Register"):
#             r = api("post", "/auth/register",
#                     json={"username": u2, "password": p2})
#             st.write("Status code:", r.status_code)   # add this
#             st.write("Raw response:", r.text)          # add this
#             if r.status_code == 200:
#                 st.session_state.token = r.json()["access_token"]
#                 st.session_state.user = u2
#                 st.rerun()
#             elif r.text:                               # only parse if not empty
#                 st.error(r.json().get("detail", "Error"))
#             else:
#                 st.error(f"Server error (status {r.status_code}) — check FastAPI terminal")

def auth_page():
    st.title("⚖️ Judiciary AI — Legal Analytics")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login"):
            try:
                r = requests.post(
                    f"{API_BASE}/auth/login",
                    data={"username": u, "password": p},
                    timeout=10
                )
                st.write("Status:", r.status_code)
                st.write("Raw response:", repr(r.text))
                if r.status_code == 200:
                    st.session_state.token = r.json()["access_token"]
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error(r.text or f"Error {r.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API at http://localhost:8000 — is uvicorn running?")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    with tab2:
        u2 = st.text_input("Username", key="reg_u")
        p2 = st.text_input("Password", type="password", key="reg_p")
        if st.button("Register"):
            try:
                r = requests.post(
                    f"{API_BASE}/auth/register",
                    json={"username": u2, "password": p2},
                    timeout=10
                )
                st.write("Status:", r.status_code)
                st.write("Raw response:", repr(r.text))
                if r.status_code == 200:
                    st.session_state.token = r.json()["access_token"]
                    st.session_state.user = u2
                    st.rerun()
                else:
                    st.error(r.text or f"Error {r.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API at http://localhost:8000 — is uvicorn running?")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

# ── Main dashboard ─────────────────────────────────────────────────────────────

def main_dashboard():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        if st.button("Logout"):
            st.session_state.token = None
            st.rerun()
        st.divider()

        # Case management
        st.markdown("### Cases")
        cases_resp = api("get", "/cases")
        cases = cases_resp.json() if cases_resp.status_code == 200 else []

        with st.expander("+ New case"):
            title = st.text_input("Case title")
            desc = st.text_area("Description", height=80)
            if st.button("Create"):
                api("post", "/cases", json={"title": title, "description": desc})
                st.rerun()

        selected_case = None
        for c in cases:
            if st.button(f"📁 {c['title']}", key=c["id"]):
                st.session_state.selected_case = c
        selected_case = st.session_state.get("selected_case")

    if not selected_case:
        st.info("Select or create a case from the sidebar to get started.")
        return

    st.title(f"⚖️ {selected_case['title']}")

    # Upload new document
    with st.expander("📤 Upload new document", expanded=True):
        file = st.file_uploader("Upload PDF, DOCX, or TXT",
                                type=["pdf", "docx", "txt"])
        # if file and st.button("Analyse document"):
        #     with st.spinner("Running NLP pipeline + AI analysis..."):
        #         r = api("post", f"/upload/{selected_case['id']}",
        #                 files={"file": (file.name, file.getvalue(), file.type)})
        # In the upload section of dashboard/app.py
        if file and st.button("Analyse document"):
            with st.spinner("Running NLP + AI analysis... (may take 30-60 seconds on first run)"):
                r = api("post", f"/upload/{selected_case['id']}",
                        files={"file": (file.name, file.getvalue(), file.type)},
                        timeout=180)   # 3 minutes for upload+analysis
            if r.status_code == 200:
                result = r.json()
                st.success("Analysis complete!")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Document summary**")
                    st.write(result.get("summary", ""))
                    st.markdown("**Document type**")
                    st.code(result.get("classification", ""))
                with col2:
                    if result.get("follow_up"):
                        st.markdown("**Follow-up (changes from previous docs)**")
                        st.info(result["follow_up"])
                st.markdown("**Suggested laws**")
                for law in result.get("laws_suggested", []):
                    st.markdown(f"- **{law.get('act')} §{law.get('section')}** — {law.get('reason','')}")
                st.markdown("**Future scope**")
                for s in result.get("future_scope", []):
                    st.markdown(f"- {s}")
            else:
                st.error(f"Upload failed ({r.status_code}): {r.text[:300]}")

    st.divider()

    # Case dashboard
    with st.spinner("Loading case dashboard..."):
        dash_r = api("get", f"/dashboard/{selected_case['id']}")

    if dash_r.status_code == 404:
        st.info("Upload at least one document to see the case dashboard.")
        return
    elif dash_r.status_code != 200:
        st.error(f"Dashboard error ({dash_r.status_code}): {dash_r.text[:300]}")
        return

    dash = dash_r.json()
    llm = dash.get("llm_dashboard", {})
    analytics = dash.get("analytics", {})

    t1, t2, t3, t4 = st.tabs(
        ["📋 Case overview", "⚖️ Laws & statutes", "🔭 Future scope", "🔔 Follow-up"]
    )

    with t1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### Cumulative case summary")
            st.write(llm.get("cumulative_summary", "No summary yet."))
            st.markdown("### Case trajectory")
            st.info(llm.get("case_trajectory", ""))
            st.markdown("### Risk assessment")
            st.warning(llm.get("risk_assessment", ""))
        with col2:
            st.markdown("### Timeline")
            for event in dash.get("timeline", []):
                st.markdown(f"**{event['date']}** — {event['doc_type']}: `{event['filename']}`")
            progress = analytics.get("progress", {})
            if progress:
                st.markdown("### Case progress")
                st.progress(progress.get("score", 0) / 100)
                st.caption(f"{progress.get('stage','Unknown')} — {progress.get('score',0)}/100")

    with t2:
        laws = analytics.get("citation_frequency", [])
        chart = analytics.get("chart_data", {})
        if chart.get("labels"):
            import plotly.express as px
            import pandas as pd
            df = pd.DataFrame({
                "Law": chart["labels"],
                "Citations": chart["frequencies"],
                "Act": chart["acts"],
            })
            fig = px.bar(df, x="Law", y="Citations", color="Act",
                         title="Act/Section citation frequency",
                         template="plotly_white")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No citation data yet.")

        st.markdown("### Consolidated laws")
        for law in llm.get("consolidated_laws", []):
            with st.expander(f"{law.get('act')} §{law.get('section')} — cited {law.get('frequency',1)}x"):
                st.write(law.get("significance", ""))

    with t3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Future scope")
            for s in llm.get("future_scope", []):
                st.markdown(f"- {s}")
        with col2:
            st.markdown("### Recommended actions")
            for a in llm.get("recommended_actions", []):
                st.markdown(f"- ✅ {a}")

    with t4:
        st.markdown("### Follow-up brief")
        st.info(llm.get("follow_up_brief", "No updates yet."))
        st.markdown("### Case status")
        st.code(llm.get("case_status", "Unknown"))


# ── Run ────────────────────────────────────────────────────────────────────────

if not st.session_state.token:
    auth_page()
else:
    main_dashboard()