 
import math
import re
from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Student Registry", page_icon="📘", layout="wide")

API_DEFAULT = "http://127.0.0.1:8000"
PAGE_SIZE = 10


class ApiError(Exception):
    pass


def api(method, path, body=None, params=None):
    base = st.session_state.api_base.rstrip("/")
    try:
        response = requests.request(
            method, base + path, json=body, params=params, timeout=15
        )
    except requests.RequestException as exc:
        log_request(method, path, "Network error", 0)
        raise ApiError(f"Cannot connect to {base}. Is FastAPI running?") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    log_request(method, path, response.status_code, response.elapsed.total_seconds() * 1000)
    if not response.ok:
        raise ApiError(data.get("detail", response.reason) if isinstance(data, dict) else response.reason)
    return data


def log_request(method, path, status, ms):
    st.session_state.request_log.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "method": method,
        "path": path,
        "status": str(status),
        "ms": round(ms),
    })
    st.session_state.request_log = st.session_state.request_log[:100]


def fetch_all_students():
    # Your backend returns: page, limit, Totalstudents, currentPage
    data = api("GET", "/students", params={"page": 1, "limit": 100})
    students = data.get("currentPage", [])
    total = int(data.get("Totalstudents", len(students)))
    pages = math.ceil(total / 100)

    for page in range(2, pages + 1):
        next_data = api("GET", "/students", params={"page": page, "limit": 100})
        students.extend(next_data.get("currentPage", []))
    return students


def grade(marks):
    if marks >= 90:
        return "A+"
    if marks >= 80:
        return "A"
    if marks >= 70:
        return "B"
    if marks >= 60:
        return "C"
    return "F"


def show_error(exc):
    detail = str(exc)
    st.error(detail)


def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


st.markdown("""
<style>
:root {
    color-scheme: dark;
    --primary-color: #d7b978;
    --background-color: #090a0c;
    --secondary-background-color: #121316;
    --text-color: #f0eee8;
    --border-color: rgba(215, 185, 120, .16);
}
.stApp, [data-testid="stAppViewContainer"] {
    background: #090a0c;
    color: #f0eee8;
}
[data-testid="stHeader"] {display: none;}
[data-testid="stSidebar"] {
    background: #101114;
    border-right: 1px solid rgba(215, 185, 120, .12);
}
.block-container {
    max-width: 1480px;
    padding: 3.5rem 2.5rem 4rem;
}
.hero-wrap {padding: 0; margin-bottom: 3rem;}
.eyebrow {
    color: #c4ae7c;
    font-size: .75rem;
    font-weight: 700;
    letter-spacing: .16em;
    text-transform: uppercase;
}
.hero {
    font-family: Georgia, serif;
    font-size: clamp(3.2rem, 7vw, 5.3rem);
    font-weight: 400;
    letter-spacing: -.055em;
    line-height: 1.04;
    margin: 1rem 0 1.1rem;
}
.hero em {color: #d7c08d; font-style: italic;}
.sub {
    color: #a5a3a5;
    max-width: 720px;
    font-size: 1.08rem;
    line-height: 1.65;
    margin: 0;
}
.block-container [data-testid="stHorizontalBlock"] {gap: 1.25rem;}
.block-container [data-testid="stVerticalBlock"] {gap: 1.25rem;}
.stat {
    min-height: 195px;
    border: 1px solid rgba(215, 185, 120, .12);
    border-radius: 19px;
    padding: 1.4rem 1.5rem;
    background: linear-gradient(145deg, #151619, #101114);
    box-shadow: 0 12px 32px rgba(0, 0, 0, .18);
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.stat:hover {
    transform: translateY(-2px);
    border-color: rgba(215, 185, 120, .3);
    box-shadow: 0 16px 38px rgba(0, 0, 0, .3);
}
.stat-icon {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    margin-bottom: 1.25rem;
    border: 1px solid rgba(215, 185, 120, .16);
    border-radius: 12px;
    background: rgba(215, 185, 120, .07);
    color: #d7c08d;
    font-size: 1.15rem;
}
.stat-label {color: #a19fa3; font-size: .9rem; font-weight: 500;}
.stat-value {
    color: #f1eee6;
    font: 400 clamp(2rem, 3vw, 2.55rem) Georgia, serif;
    line-height: 1.15;
    margin: .65rem 0 .45rem;
}
.stat-note {color: #868489;}
.stMarkdown, .stText, label, [data-testid="stCaptionContainer"] {color: #e8e5de;}
.stMarkdown p, [data-testid="stCaptionContainer"] p {color: #aaa8aa;}
.stTabs [data-baseweb="tab-list"] {
    gap: .6rem;
    margin-top: 1.5rem;
    border-bottom: 1px solid rgba(215, 185, 120, .14);
}
.stTabs [data-baseweb="tab-panel"] {padding-top: 1.75rem;}
.stTabs [data-baseweb="tab"] {
    height: 3rem;
    padding: 0 1rem;
    border-radius: 10px 10px 0 0;
    font-weight: 600;
    color: #aaa8aa;
}
.stTabs [aria-selected="true"] {
    color: #e5d2a2;
    background: rgba(215, 185, 120, .08);
}
.stButton > button, .stFormSubmitButton > button {
    border: 1px solid rgba(215, 185, 120, .22);
    border-radius: 10px;
    font-weight: 600;
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #f0d99f, #c5a666);
    color: #16130d;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, .1);
}
[data-baseweb="input"] > div, [data-baseweb="select"] > div,
[data-baseweb="textarea"] > div, [data-testid="stNumberInput"] input {
    background: #141518;
    border-color: rgba(215, 185, 120, .18);
    color: #f0eee8;
}
[data-testid="stExpander"] {
    border: 1px solid rgba(215, 185, 120, .16);
    border-radius: 13px;
    background: #111214;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: rgba(215, 185, 120, .16);
    border-radius: 16px;
    background: linear-gradient(145deg, rgba(20, 21, 24, .72), rgba(13, 14, 16, .72));
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(215, 185, 120, .14);
    border-radius: 13px;
    overflow: hidden;
    margin: .5rem 0 1rem;
}
[data-testid="stMetric"] {
    padding: 1rem;
    border: 1px solid rgba(215, 185, 120, .14);
    border-radius: 13px;
    background: #121316;
}
hr {
    border-color: rgba(215, 185, 120, .14);
    margin: 2rem 0;
}
.stButton > button {min-height: 2.7rem;}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {min-height: 2.8rem;}
@media (max-width: 700px) {
    .block-container {padding: 2rem 1rem 2.5rem;}
    .block-container [data-testid="stHorizontalBlock"] {gap: .7rem;}
    .hero {font-size: clamp(2.7rem, 12vw, 4rem);}
    .hero-wrap {margin-bottom: 2rem;}
    .stat {min-height: 170px; padding: 1rem;}
    .stat-value {font-size: 1.8rem;}
}
</style>
""", unsafe_allow_html=True)

st.session_state.setdefault("api_base", API_DEFAULT)
st.session_state.setdefault("request_log", [])
st.session_state.setdefault("page", 1)
st.session_state.setdefault("selected_id", None)

with st.sidebar:
    st.subheader("Backend connection")
    st.text_input("FastAPI URL", key="api_base")
    st.caption("Local URL: http://127.0.0.1:8000")
    if st.button("Refresh records", use_container_width=True):
        st.rerun()

try:
    all_students = fetch_all_students()
except ApiError as exc:
    st.markdown(
        '<div class="hero-wrap"><div class="eyebrow">Academic dashboard</div>'
        '<div class="hero">Student <em>records</em></div></div>',
        unsafe_allow_html=True,
    )
    st.error("Unable to load data from FastAPI.")
    show_error(exc)
    st.info("Start your backend with: `uvicorn main:app --reload`")
    st.stop()

by_id = {s["id"]: s for s in all_students}
courses = sorted({s["course"] for s in all_students}, key=str.lower)
n = len(all_students)
avg_marks = sum(s["marks"] for s in all_students) / n if n else 0
avg_age = sum(s["age"] for s in all_students) / n if n else 0
topper = max(all_students, key=lambda s: s["marks"]) if n else None

st.markdown(
    f'<div class="hero-wrap"><div class="eyebrow">{datetime.now():%A, %d %B %Y}</div>'
    '<div class="hero">Student <em>records</em></div>'
    '<div class="sub">Enrol, review and manage every student in one place, backed live by your FastAPI service.</div></div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
cards = [
    ("♙", "Total students", n, f"Across {len(courses)} courses"),
    ("↗", "Average marks", f"{avg_marks:.1f}", "Out of 100"),
    ("◷", "Average age", f"{avg_age:.1f}", "Years"),
    ("✦", "Top scorer", topper["marks"] if topper else "—", topper["name"] if topper else "No records"),
]
for col, (icon, label, value, note) in zip([c1, c2, c3, c4], cards):
    col.markdown(f'<div class="stat"><div class="stat-icon">{icon}</div>'
                 f'<div class="stat-label">{label}</div>'
                 f'<div class="stat-value">{value}</div><small class="stat-note">{note}</small></div>',
                 unsafe_allow_html=True)

tab_roster, tab_insights, tab_activity = st.tabs(
    ["📚 Student roster", "📊 Insights", "⚡ API activity"]
)

with tab_roster:
    st.subheader("Student records")
    st.caption("Create new records, browse the roster, or manage an individual student.")
    with st.expander("＋  Add a student"):
        with st.form("create_student"):
            a, b = st.columns(2)
            sid = a.text_input("Student ID", placeholder="S101")
            name = b.text_input("Name")
            email = a.text_input("Email")
            course = b.text_input("Course")
            age = a.number_input("Age", min_value=0, max_value=100, value=20)
            marks = b.number_input("Marks", min_value=0, max_value=100, value=75)
            submitted = st.form_submit_button("Create student", type="primary")

        if submitted:
            payload = {
                "id": sid.strip(), "name": name.strip(), "age": int(age),
                "course": course.strip(), "marks": int(marks), "email": email.strip()
            }
            errors = []
            if not payload["id"]:
                errors.append("Student ID is required.")
            if not 3 <= len(payload["name"]) <= 50:
                errors.append("Name must have 3–50 characters.")
            if not payload["name"].replace(" ", "").isalpha():
                errors.append("Name must contain only letters and spaces.")
            if not 5 <= len(payload["course"]) <= 30:
                errors.append("Course must have 5–30 characters.")
            if not valid_email(payload["email"]):
                errors.append("Enter a valid email.")
            if payload["id"] in by_id:
                errors.append("Student ID already exists.")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    # Exact backend route: POST /Create
                    created = api("POST", "/Create", body=payload)
                    st.success(f"Created {created['name']} — grade {created['grade']}")
                    st.session_state.selected_id = created["id"]
                    st.rerun()
                except ApiError as exc:
                    show_error(exc)

    st.divider()
    with st.container(border=True):
        st.subheader("Browse roster")
        st.caption("Search and filter the records, then choose how they should be ordered.")

        f1, f2, f3 = st.columns([2, 1, 1])
        search = f1.text_input("Search name, email or ID")
        course_filter = f2.selectbox("Course", ["All"] + courses)
        sort_by = f3.selectbox("Sort by", ["ID", "Name", "Age", "Marks"])

        f4, f5, f6 = st.columns([1, 2, 1])
        order = f4.selectbox("Order", ["Ascending", "Descending"])
        marks_range = f5.slider("Marks range", 0, 100, (0, 100))
        page_size = f6.selectbox("Rows per page", [5, 10, 20, 50], index=1)

        rows = list(all_students)
        if course_filter != "All":
            rows = [s for s in rows if s["course"].lower() == course_filter.lower()]
        if search.strip():
            q = search.strip().lower()
            rows = [s for s in rows if q in s["id"].lower() or q in s["name"].lower()
                    or q in s["email"].lower()]
        rows = [s for s in rows if marks_range[0] <= s["marks"] <= marks_range[1]]

        sort_key = {"ID": "id", "Name": "name", "Age": "age", "Marks": "marks"}[sort_by]
        rows.sort(key=lambda s: s[sort_key].lower() if isinstance(s[sort_key], str) else s[sort_key],
                  reverse=order == "Descending")

        total = len(rows)
        pages = max(1, math.ceil(total / page_size))
        st.session_state.page = min(st.session_state.page, pages)
        start = (st.session_state.page - 1) * page_size
        visible = rows[start:start + page_size]

        st.caption(f"Showing {len(visible)} of {total} students · sorted by {sort_by.lower()} ({order.lower()})")
        if visible:
            table = pd.DataFrame([{
                "ID": s["id"], "Name": s["name"], "Course": s["course"],
                "Age": s["age"], "Marks": s["marks"],
                "Grade": s.get("grade", grade(s["marks"])), "Email": s["email"]
            } for s in visible])
            st.dataframe(table, hide_index=True, use_container_width=True)
        else:
            st.info("No students match these filters.")

        p1, p2, p3 = st.columns([1, 2, 1])
        if p1.button("← Previous", disabled=st.session_state.page <= 1):
            st.session_state.page -= 1
            st.rerun()
        p2.markdown(
            f"<div style='text-align:center;padding-top:10px'>Page {st.session_state.page} / {pages}</div>",
            unsafe_allow_html=True,
        )
        if p3.button("Next →", disabled=st.session_state.page >= pages):
            st.session_state.page += 1
            st.rerun()

    st.divider()
    with st.container(border=True):
        st.subheader("Find a student")
        st.caption("Look up a record by its student ID to view, update, or delete it.")
        g1, g2 = st.columns([2, 1])
        lookup_id = g1.text_input("Enter student ID", key="lookup_id")
        if g2.button("Get student", use_container_width=True):
            try:
                # Exact backend route: GET /student/{student_id}
                student = api("GET", f"/student/{requests.utils.quote(lookup_id.strip())}")
                st.session_state.selected_id = student["id"]
                st.rerun()
            except ApiError as exc:
                show_error(exc)

    selected = by_id.get(st.session_state.selected_id)
    if selected:
        st.divider()
        st.subheader(f"Profile: {selected['name']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ID", selected["id"])
        m2.metric("Age", selected["age"])
        m3.metric("Marks", selected["marks"])
        m4.metric("Grade", selected.get("grade", grade(selected["marks"])))

        with st.expander("✎ Update student"):
            with st.form(f"update_{selected['id']}"):
                u1, u2 = st.columns(2)
                new_name = u1.text_input("Name", value=selected["name"])
                new_email = u2.text_input("Email", value=selected["email"])
                new_course = u1.text_input("Course", value=selected["course"])
                new_age = u2.number_input("Age", 1, 100, max(1, selected["age"]))
                new_marks = u1.number_input("Marks", 1, 100, max(1, selected["marks"]))
                save = st.form_submit_button("Save changes", type="primary")

            if save:
                values = {
                    "name": new_name.strip(), "email": new_email.strip(),
                    "course": new_course.strip(), "age": int(new_age), "marks": int(new_marks)
                }
                changes = {k: v for k, v in values.items() if v != selected[k]}
                errors = []
                if "name" in changes and (
                    not 3 <= len(changes["name"]) <= 50
                    or not changes["name"].replace(" ", "").isalpha()
                ):
                    errors.append("Name must be 3–50 letters/spaces.")
                if "course" in changes and not 5 <= len(changes["course"]) <= 30:
                    errors.append("Course must have 5–30 characters.")
                if "email" in changes and not valid_email(changes["email"]):
                    errors.append("Enter a valid email.")
                if errors:
                    for error in errors:
                        st.error(error)
                elif not changes:
                    st.info("No changes to save.")
                else:
                    try:
                        # Exact backend route: PUT /Update/{student_id}
                        updated = api("PUT", f"/Update/{requests.utils.quote(selected['id'])}",
                                      body=changes)
                        st.success(f"Updated {updated['name']}.")
                        st.rerun()
                    except ApiError as exc:
                        show_error(exc)

        with st.expander("🗑 Delete student"):
            st.warning(f"This deletes {selected['name']} from the PostgreSQL database.")
            confirm = st.text_input(f"Type {selected['id']} to confirm",
                                    key=f"confirm_{selected['id']}")
            if st.button("Delete permanently", type="primary",
                         disabled=confirm.strip() != selected["id"]):
                try:
                    # Exact backend route: DELETE /delete/{student_id}
                    deleted = api("DELETE", f"/delete/{requests.utils.quote(selected['id'])}")
                    st.success(f"Deleted {deleted['name']}.")
                    st.session_state.selected_id = None
                    st.rerun()
                except ApiError as exc:
                    show_error(exc)

with tab_insights:
    st.subheader("Academic insights")
    st.caption("Explore course averages, grade distribution, and the relationship between age and marks.")
    if not all_students:
        st.info("Add students to see insights.")
    else:
        df = pd.DataFrame(all_students)
        df["grade"] = df["marks"].apply(grade)
        left, right = st.columns(2)
        with left:
            st.markdown("#### Average marks by course")
            avg = df.groupby("course", as_index=False)["marks"].mean()
            chart = alt.Chart(avg).mark_bar().encode(
                x=alt.X("marks:Q", title="Average marks"),
                y=alt.Y("course:N", sort="-x", title="Course"),
                tooltip=["course", alt.Tooltip("marks:Q", format=".1f")]
            )
            st.altair_chart(chart, use_container_width=True)
        with right:
            st.markdown("#### Grade distribution")
            counts = df.groupby("grade").size().reset_index(name="students")
            chart = alt.Chart(counts).mark_bar().encode(
                x=alt.X("grade:N", sort=["A+", "A", "B", "C", "F"]),
                y="students:Q", tooltip=["grade", "students"]
            )
            st.altair_chart(chart, use_container_width=True)
        st.markdown("#### Age vs marks")
        scatter = alt.Chart(df).mark_circle(size=120).encode(
            x="age:Q", y="marks:Q", color="course:N",
            tooltip=["id", "name", "course", "age", "marks", "grade"]
        ).interactive()
        st.altair_chart(scatter, use_container_width=True)

with tab_activity:
    st.subheader("API activity")
    st.caption("Recent requests made by this dashboard, plus an export of the current student records.")
    if st.session_state.request_log:
        st.dataframe(pd.DataFrame(st.session_state.request_log),
                     hide_index=True, use_container_width=True)
        if st.button("Clear activity"):
            st.session_state.request_log = []
            st.rerun()
    else:
        st.info("No API requests yet.")
    st.download_button(
        "Download students CSV",
        pd.DataFrame(all_students).to_csv(index=False),
        file_name="students.csv",
        mime="text/csv",
        disabled=not all_students,
    )
