"""
SVIES — Dashboard Application
Streamlit fallback dashboard (legacy).
The primary dashboard is the React frontend in svies/frontend/.

Usage:
    streamlit run dashboard/app.py

For the React dashboard:
    cd svies/frontend && npm run dev
"""

import sys
from pathlib import Path

# ── Ensure project root on path ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import streamlit as st
except ImportError:
    print("=" * 60)
    print("SVIES Dashboard")
    print("=" * 60)
    print()
    print("Streamlit is not installed.")
    print("The primary dashboard is now a React application.")
    print()
    print("To start the React dashboard:")
    print("  1. Start the backend:  uvicorn api.server:app --reload --port 8000")
    print("  2. Start the frontend: cd frontend && npm run dev")
    print()
    print("  Backend API docs:  http://localhost:8000/docs")
    print("  React Dashboard:   http://localhost:5173")
    print()
    print("Alternatively, use Docker:")
    print("  docker-compose up --build")
    print("  Frontend: http://localhost:3000  |  Backend: http://localhost:8000")
    print()
    sys.exit(0)

import pandas as pd
import json
from datetime import datetime, timezone

from modules.offender_tracker import get_all_violations, get_top_offenders, get_violation_history
from modules.mock_db_loader import lookup_vahan, lookup_pucc, lookup_insurance, is_stolen
from modules.geofence import get_all_zones


# ══════════════════════════════════════════════════════════
# Page Config
# ══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="SVIES Dashboard",
    page_icon="🚔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom dark theme via CSS ──
st.markdown("""
<style>
    .stApp { background-color: #0f0f1a; }
    .stMetric label { color: #a0aec0 !important; }
    .stMetric [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════

st.sidebar.title("🚔 SVIES")
st.sidebar.caption("Smart Vehicle Intelligence & Enforcement System")
page = st.sidebar.radio("Navigate", [
    "📊 Overview",
    "🚨 Violations",
    "📈 Analytics",
    "🏆 Offenders",
    "🗺️ Zone Map",
    "🔍 Vehicle Lookup",
])

days = st.sidebar.slider("Time Window (days)", 1, 90, 30)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Tip:** For the full React dashboard experience, run:\n```\ncd frontend && npm run dev\n```"
)


# ══════════════════════════════════════════════════════════
# Page: Overview
# ══════════════════════════════════════════════════════════

if page == "📊 Overview":
    st.title("📊 Dashboard Overview")

    violations = get_all_violations(days=days)
    total = len(violations)
    critical = sum(1 for v in violations if v.get("alert_level") == "CRITICAL")
    high = sum(1 for v in violations if v.get("alert_level") == "HIGH")
    medium = sum(1 for v in violations if v.get("alert_level") == "MEDIUM")
    low = sum(1 for v in violations if v.get("alert_level") == "LOW")
    unique = len(set(v.get("plate", "") for v in violations))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Violations", total)
    c2.metric("🔴 Critical", critical)
    c3.metric("🟠 High", high)
    c4.metric("🟡 Medium", medium)
    c5.metric("🟢 Low", low)

    st.metric("Unique Vehicles", unique)

    if violations:
        st.subheader("Recent Violations")
        df = pd.DataFrame(violations[:50])
        if not df.empty:
            cols = [c for c in ["timestamp", "plate", "violation_types", "risk_score", "alert_level"] if c in df.columns]
            st.dataframe(df[cols] if cols else df, use_container_width=True)
    else:
        st.info("No violations found in the selected time window.")


# ══════════════════════════════════════════════════════════
# Page: Violations
# ══════════════════════════════════════════════════════════

elif page == "🚨 Violations":
    st.title("🚨 Violation Log")

    col1, col2 = st.columns(2)
    search_plate = col1.text_input("Search by plate", "")
    filter_level = col2.multiselect("Filter by severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    violations = get_all_violations(days=days)

    if search_plate:
        violations = [v for v in violations if search_plate.upper() in v.get("plate", "").upper()]
    if filter_level:
        violations = [v for v in violations if v.get("alert_level") in filter_level]

    st.write(f"**{len(violations)}** violation(s) found")

    if violations:
        df = pd.DataFrame(violations)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No violations match your filters.")


# ══════════════════════════════════════════════════════════
# Page: Analytics
# ══════════════════════════════════════════════════════════

elif page == "📈 Analytics":
    st.title("📈 Analytics")

    violations = get_all_violations(days=days)

    if not violations:
        st.info("No data for analytics.")
    else:
        # ── Daily counts ──
        daily = {}
        for v in violations:
            ts = v.get("timestamp", "")
            if len(ts) >= 10:
                day = ts[:10]
                daily[day] = daily.get(day, 0) + 1

        if daily:
            st.subheader("Daily Violations")
            df_daily = pd.DataFrame(sorted(daily.items()), columns=["Date", "Count"])
            st.bar_chart(df_daily.set_index("Date"))

        # ── Level distribution ──
        st.subheader("Alert Level Distribution")
        levels = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for v in violations:
            lvl = v.get("alert_level", "LOW")
            levels[lvl] = levels.get(lvl, 0) + 1
        df_levels = pd.DataFrame(list(levels.items()), columns=["Level", "Count"])
        st.bar_chart(df_levels.set_index("Level"))

        # ── Violation types ──
        st.subheader("Top Violation Types")
        type_counts = {}
        for v in violations:
            for vt in (v.get("violation_types") or "").split(","):
                vt = vt.strip()
                if vt:
                    type_counts[vt] = type_counts.get(vt, 0) + 1
        if type_counts:
            df_types = pd.DataFrame(sorted(type_counts.items(), key=lambda x: -x[1])[:10],
                                     columns=["Type", "Count"])
            st.bar_chart(df_types.set_index("Type"))


# ══════════════════════════════════════════════════════════
# Page: Offenders
# ══════════════════════════════════════════════════════════

elif page == "🏆 Offenders":
    st.title("🏆 Repeat Offenders")

    offenders = get_top_offenders(limit=20, days=days)

    if not offenders:
        st.info("No repeat offenders found.")
    else:
        for i, o in enumerate(offenders, 1):
            plate = o.get("plate", "?")
            count = o.get("count", 0)
            vahan = lookup_vahan(plate)
            owner = vahan.get("owner", "Unknown") if vahan else "Unknown"

            with st.expander(f"#{i} — {plate} ({count} violations) — {owner}"):
                history = get_violation_history(plate, days=days)
                if history:
                    df = pd.DataFrame(history)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.write("No violation history.")


# ══════════════════════════════════════════════════════════
# Page: Zone Map
# ══════════════════════════════════════════════════════════

elif page == "🗺️ Zone Map":
    st.title("🗺️ Geofence Zone Map")

    zones = get_all_zones()

    if not zones:
        st.info("No zones configured.")
    else:
        st.write(f"**{len(zones)}** zones configured")

        for z in zones:
            ztype = z.get("type", "?")
            zname = z.get("name", z.get("zone_id", "?"))
            priority = z.get("priority", "?")
            coords = z.get("polygon", [])
            st.write(f"- **{zname}** ({ztype}) — Priority: {priority}, Vertices: {len(coords)}")

        st.info("For an interactive map, use the React dashboard at http://localhost:5173/zones")


# ══════════════════════════════════════════════════════════
# Page: Vehicle Lookup
# ══════════════════════════════════════════════════════════

elif page == "🔍 Vehicle Lookup":
    st.title("🔍 Vehicle Lookup")

    plate = st.text_input("Enter License Plate Number", "").upper().strip()

    if plate:
        vahan = lookup_vahan(plate)
        pucc = lookup_pucc(plate)
        insurance = lookup_insurance(plate)
        stolen = is_stolen(plate)

        if vahan:
            st.subheader("📋 Registration Details")
            for k, v in vahan.items():
                st.write(f"**{k}:** {v}")
        else:
            st.warning("Vehicle not found in VAHAN database.")

        c1, c2, c3 = st.columns(3)
        with c1:
            pucc_status = pucc.get("status", "NOT_FOUND") if pucc else "NOT_FOUND"
            color = "🟢" if pucc_status == "VALID" else "🔴"
            st.metric("PUCC", f"{color} {pucc_status}")
        with c2:
            ins_status = insurance.get("status", "NOT_FOUND") if insurance else "NOT_FOUND"
            color = "🟢" if ins_status == "VALID" else "🔴"
            st.metric("Insurance", f"{color} {ins_status}")
        with c3:
            color = "🔴" if stolen else "🟢"
            st.metric("Stolen", f"{color} {'YES' if stolen else 'NO'}")

        # ── Violation history ──
        history = get_violation_history(plate, days=90)
        if history:
            st.subheader("📜 Violation History")
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)
        else:
            st.success("No violations found!")
