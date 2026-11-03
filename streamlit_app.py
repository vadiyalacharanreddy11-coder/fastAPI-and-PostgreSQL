 
#  """
# Student Registry - Streamlit frontend for the FastAPI student-management backend.

# Backend routes used
#     POST   /signUp               -> {access_token}
#     POST   /logIn                -> {access_token}
#     GET    /students             -> {page, limit, Totalstudents, currentPage}   (JWT)
#     GET    /student/{id}         -> student                                     (JWT)
#     POST   /Create               -> student                                     (JWT)
#     PUT    /Update/{id}          -> student                                     (JWT)
#     DELETE /delete/{id}          -> student                                     (JWT)

# Run:  streamlit run app.py
# """

import math
import re
from datetime import datetime
from urllib.parse import quote

import altair as alt
import pandas as pd
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Student Registry", page_icon="🎓", layout="wide")

API_DEFAULT = "https://student-management-api-tr9q.onrender.com"
<<<<<<< HEAD
PAGE_SIZE = 10
=======
TIMEOUT = 60  # Render free tier can take ~30s to wake up

st.session_state.setdefault("api_base", API_DEFAULT)
st.session_state.setdefault("request_log", [])
st.session_state.setdefault("page", 1)
st.session_state.setdefault("selected_id", None)
st.session_state.setdefault("token", None)
st.session_state.setdefault("user_email", None)
st.session_state.setdefault("user_name", None)
st.session_state.setdefault("flash", None)
>>>>>>> 3a7445f (ch)


# ─────────────────────────────────────────────────────────────────────────────
# 2. API LAYER
# ─────────────────────────────────────────────────────────────────────────────
class ApiError(Exception):
    pass


class AuthExpired(ApiError):
    """Raised when the backend rejects our JWT (expired / invalid)."""


def format_detail(detail):
    """FastAPI returns a string for HTTPException and a list for 422 errors."""
    if isinstance(detail, list):
        parts = []
        for item in detail:
            loc = ".".join(str(x) for x in item.get("loc", [])[1:])
            msg = item.get("msg", "Invalid value")
            parts.append(f"{loc}: {msg}" if loc else msg)
        return " · ".join(parts)
    return str(detail)


def log_request(method, path, status, ms):
    st.session_state.request_log.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "method": method,
        "path": path,
        "status": str(status),
        "ms": round(ms),
    })
    st.session_state.request_log = st.session_state.request_log[:100]


def api(method, path, body=None, params=None, auth=True):
    base = st.session_state.api_base.rstrip("/")
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        response = requests.request(
            method, base + path, json=body, params=params,
            headers=headers, timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        log_request(method, path, "Network error", 0)
        raise ApiError(f"Cannot reach {base}. Check the URL or whether the server is running.") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    log_request(method, path, response.status_code, response.elapsed.total_seconds() * 1000)

    if response.status_code == 401 and auth and st.session_state.token:
        raise AuthExpired("Your session has expired. Please sign in again.")
    if not response.ok:
        detail = data.get("detail", response.reason) if isinstance(data, dict) else response.reason
        raise ApiError(format_detail(detail))
    return data


def fetch_all_students():
    data = api("GET", "/students", params={"page": 1, "limit": 100})
    students = data.get("currentPage", [])
    total = int(data.get("Totalstudents", len(students)))
    for page in range(2, math.ceil(total / 100) + 1):
        students.extend(api("GET", "/students", params={"page": page, "limit": 100}).get("currentPage", []))
    return students


# ─────────────────────────────────────────────────────────────────────────────
# 3. HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def login_user(token, email, name=None):
    st.session_state.token = token
    st.session_state.user_email = email
    st.session_state.user_name = name or email.split("@")[0].replace(".", " ").title()
    st.session_state.page = 1
    st.session_state.selected_id = None
    st.rerun()


def logout(message=None):
    for key in ("token", "user_email", "user_name", "selected_id"):
        st.session_state[key] = None
    st.session_state.page = 1
    st.session_state.flash = message


def show_error(exc):
    if isinstance(exc, AuthExpired):
        logout(str(exc))
        st.rerun()
    st.error(str(exc))


def flash(message):
    """Show a message after the next rerun."""
    st.session_state.flash = message


def greeting():
    hour = datetime.now().hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


# ─────────────────────────────────────────────────────────────────────────────
# 4. STYLES  (light, chalk-blue theme to match the sign-up reference)
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&display=swap');

:root {
    --ink: #14213d;
    --muted: #64748b;
    --paper: #f3f7fc;
    --card: #ffffff;
    --blue: #2563eb;
    --blue-dark: #1d4ed8;
    --sky: #dbeafe;
    --chalk: #ffd166;
    --line: #e2e8f0;
}
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: var(--paper);
    color: var(--ink);
    font-family: 'Figtree', system-ui, sans-serif;
}
[data-testid="stHeader"], footer, #MainMenu {display: none;}
h1, h2, h3, h4, .display {font-family: 'Bricolage Grotesque', 'Figtree', sans-serif; color: var(--ink); letter-spacing: -.02em;}
.stMarkdown p, label, [data-testid="stCaptionContainer"] p {color: var(--muted);}
label p {color: var(--ink) !important; font-weight: 600; font-size: .86rem;}

.block-container {max-width: 1380px; padding: 2.2rem 2.4rem 4rem;}
[data-testid="stSidebar"] {background: #ffffff; border-right: 1px solid var(--line);}

/* ── inputs ── */
[data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-baseweb="textarea"] > div,
[data-testid="stNumberInput"] input {
    background: #f8fafc !important; border: 1px solid var(--line) !important;
    border-radius: 10px !important; color: var(--ink) !important;
}
[data-baseweb="input"] input {color: var(--ink) !important; background: transparent !important;}
[data-baseweb="input"] > div:focus-within, [data-baseweb="select"] > div:focus-within {
    border-color: var(--blue) !important; box-shadow: 0 0 0 3px rgba(37,99,235,.14) !important;
}

/* ── buttons ── */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    min-height: 2.75rem; border-radius: 10px; font-weight: 700;
    border: 1px solid var(--line); background: #fff; color: var(--ink);
    transition: transform .12s ease, box-shadow .12s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {transform: translateY(-1px); border-color: var(--blue); color: var(--blue);}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: var(--blue); color: #fff; border: none; box-shadow: 0 6px 16px rgba(37,99,235,.28);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {background: var(--blue-dark); color: #fff;}

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] {gap: .35rem; background: #eaf0f8; padding: .3rem; border-radius: 12px; border: none; width: fit-content;}
.stTabs [data-baseweb="tab"] {height: 2.5rem; padding: 0 1.1rem; border-radius: 9px; font-weight: 700; color: var(--muted);}
.stTabs [aria-selected="true"] {background: #fff; color: var(--blue); box-shadow: 0 1px 4px rgba(20,33,61,.1);}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display: none;}
.stTabs [data-baseweb="tab-panel"] {padding-top: 1.4rem;}

/* ── containers ── */
[data-testid="stVerticalBlockBorderWrapper"] {border-color: var(--line); border-radius: 16px; background: #fff;}
[data-testid="stExpander"] {border: 1px solid var(--line); border-radius: 14px; background: #fff;}
[data-testid="stDataFrame"] {border: 1px solid var(--line); border-radius: 12px; overflow: hidden;}
[data-testid="stMetric"] {background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.2rem;}
[data-testid="stForm"] {border: none; padding: 0; background: transparent;}
hr {border-color: var(--line); margin: 1.6rem 0;}

/* ── dashboard hero + stat cards ── */
.hero {font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: clamp(2.2rem, 4.6vw, 3.6rem);
       line-height: 1.05; letter-spacing: -.04em; color: var(--ink); margin: 0 0 .6rem;}
.hero span {background: linear-gradient(transparent 62%, var(--chalk) 62%); padding: 0 .15em;}
.sub {color: var(--muted); font-size: 1.05rem; max-width: 640px; margin-bottom: 2rem;}
.stat {background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 1.3rem 1.4rem; min-height: 170px;}
.stat.hot {background: var(--blue); border-color: var(--blue); color: #fff; box-shadow: 0 14px 30px rgba(37,99,235,.3);}
.stat-icon {width: 38px; height: 38px; border-radius: 11px; background: var(--sky); display: grid; place-items: center; font-size: 1.1rem; margin-bottom: 1rem;}
.stat.hot .stat-icon {background: rgba(255,255,255,.18);}
.stat-label {font-weight: 600; font-size: .88rem; color: var(--muted);}
.stat.hot .stat-label, .stat.hot .stat-note {color: #dbe7ff;}
.stat-value {font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 2.3rem; line-height: 1.1; margin: .3rem 0;}
.stat-note {font-size: .82rem; color: var(--muted);}
.user-chip {display: flex; gap: .7rem; align-items: center; padding: .7rem; background: var(--paper); border-radius: 12px; margin-bottom: 1rem;}
.avatar {width: 38px; height: 38px; border-radius: 50%; background: var(--blue); color: #fff; display: grid; place-items: center; font-weight: 800;}
.user-chip b {display: block; color: var(--ink); font-size: .92rem;}
.user-chip small {color: var(--muted);}

/* ── auth page: illustration scene ── */
.scene {position: relative; height: 640px; border-radius: 26px 0 0 26px; overflow: hidden;
        background: radial-gradient(circle at 30% 20%, #ffffff 0%, #e8f1fb 55%, #d5e6f7 100%);}
.scene .ring {position: absolute; border-radius: 50%; border: 1.5px dashed rgba(37,99,235,.25);}
.scene .r1 {width: 360px; height: 360px; left: 50%; top: 46%; transform: translate(-50%,-50%);}
.scene .r2 {width: 520px; height: 520px; left: 50%; top: 46%; transform: translate(-50%,-50%); border-color: rgba(37,99,235,.12);}
.chip {position: absolute; background: #fff; border-radius: 14px; padding: .55rem .85rem; font-weight: 700; font-size: .82rem;
       color: var(--ink); box-shadow: 0 10px 24px rgba(20,33,61,.12); display: flex; gap: .45rem; align-items: center;}
.c1 {left: 7%;  top: 12%; animation: bob 6s ease-in-out infinite;}
.c2 {right: 7%; top: 20%; animation: bob 7s ease-in-out -2s infinite;}
.c3 {left: 6%;  top: 56%; animation: bob 8s ease-in-out -4s infinite;}
.c4 {right: 8%; top: 62%; animation: bob 6.5s ease-in-out -1s infinite;}
.c5 {left: 30%; top: 5%;  animation: bob 7.5s ease-in-out -3s infinite;}
.dot {width: 8px; height: 8px; border-radius: 50%; background: #22c55e;}
.card-main {position: absolute; left: 50%; top: 46%; transform: translate(-50%,-50%); width: 250px; background: #fff;
            border-radius: 22px; padding: 1.2rem; box-shadow: 0 24px 50px rgba(37,99,235,.2);}
.card-main .who {display: flex; gap: .7rem; align-items: center; margin-bottom: 1rem;}
.card-main .pic {width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg,#60a5fa,#2563eb); display: grid; place-items: center; font-size: 1.4rem;}
.card-main .who b {display: block; color: var(--ink);}
.card-main .who small {color: var(--muted);}
.bar {height: 8px; border-radius: 99px; background: #e8eef7; margin: .45rem 0 .8rem; overflow: hidden;}
.bar i {display: block; height: 100%; border-radius: 99px; background: var(--blue);}
.row {display: flex; justify-content: space-between; font-size: .78rem; color: var(--muted); font-weight: 600;}
.grade {margin-top: .4rem; display: inline-block; background: var(--chalk); color: #5b4300; font-weight: 800; padding: .15rem .65rem; border-radius: 99px; font-size: .8rem;}
.scene-cap {position: absolute; left: 0; right: 0; bottom: 1.8rem; text-align: center; padding: 0 2rem;}
.scene-cap h3 {margin: 0; font-size: 1.35rem;}
.scene-cap p {margin: .3rem 0 0; font-size: .9rem; color: var(--muted);}
@keyframes bob {0%,100% {transform: translateY(0);} 50% {transform: translateY(-10px);}}
@media (prefers-reduced-motion: reduce) {.chip {animation: none;}}

/* ── auth page: form panel ── */
.st-key-auth_form {background: #fff; border-radius: 0 26px 26px 0; padding: 2.6rem 2.8rem; min-height: 640px;
                   box-shadow: 0 30px 60px rgba(20,33,61,.08);}
.auth-title {font-family: 'Bricolage Grotesque', sans-serif; font-size: 2rem; font-weight: 800; margin: 0; color: var(--ink);}
.auth-sub {color: var(--muted); margin: .2rem 0 1.2rem;}

@media (max-width: 900px) {
    .scene {display: none;}
    .st-key-auth_form {border-radius: 22px; padding: 1.6rem;}
    .block-container {padding: 1rem;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

SCENE_HTML = """
<div class="scene">
  <div class="ring r1"></div><div class="ring r2"></div>
  <div class="chip c1">🎓 New enrolment</div>
  <div class="chip c2"><span class="dot"></span> Record saved</div>
  <div class="chip c3">🔑 ••••••••</div>
  <div class="chip c4">📈 Class average 86.4</div>
  <div class="chip c5">🛡️ Private to you</div>
  <div class="card-main">
    <div class="who"><div class="pic">🧑‍🎓</div><div><b>Aarav Sharma</b><small>Computer Science</small></div></div>
    <div class="row"><span>Marks</span><span>92 / 100</span></div>
    <div class="bar"><i style="width:92%"></i></div>
    <div class="row"><span>Attendance</span><span>96%</span></div>
    <div class="bar"><i style="width:96%; background:#60a5fa"></i></div>
    <span class="grade">Grade A+</span>
  </div>
  <div class="scene-cap">
    <h3>Every student, one clear record.</h3>
    <p>Your roster stays private to your account.</p>
  </div>
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
# 5. AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────
def auth_page():
    st.write("")
    _, mid, _ = st.columns([0.3, 5, 0.3])
    with mid:
        left, right = st.columns([1.1, 1], gap="small")
        with left:
            st.markdown(SCENE_HTML, unsafe_allow_html=True)
        with right:
            with st.container(key="auth_form"):
                if st.session_state.flash:
                    st.warning(st.session_state.flash)
                    st.session_state.flash = None

                tab_in, tab_up = st.tabs(["Sign in", "Create account"])

                # ── Sign in ──
                with tab_in:
                    st.markdown('<p class="auth-title">Welcome back</p>'
                                '<p class="auth-sub">Sign in to manage your students.</p>',
                                unsafe_allow_html=True)
                    with st.form("login_form"):
                        email = st.text_input("Email", placeholder="you@school.com")
                        password = st.text_input("Password", type="password", placeholder="Your password")
                        go = st.form_submit_button("Sign in", type="primary", use_container_width=True)
                    if go:
                        if not valid_email(email.strip()) or not password:
                            st.error("Enter your email and password.")
                        else:
                            try:
                                with st.spinner("Signing in… the server may take a few seconds to wake up."):
                                    data = api("POST", "/logIn", body={
                                        "emailId": email.strip(), "password": password}, auth=False)
                                login_user(data["access_token"], email.strip())
                            except ApiError as exc:
                                st.error(str(exc))
                                if "doesn't exist" in str(exc):
                                    st.info("No account yet? Open the Create account tab.")

                # ── Create account ──
                with tab_up:
                    st.markdown('<p class="auth-title">Create account</p>'
                                '<p class="auth-sub">It takes less than a minute.</p>',
                                unsafe_allow_html=True)
                    with st.form("signup_form"):
                        n1, n2 = st.columns(2)
                        first = n1.text_input("First name", placeholder="Charan")
                        last = n2.text_input("Last name", placeholder="Reddy")
                        s_email = st.text_input("Email", placeholder="you@school.com", key="su_email")
                        p1, p2 = st.columns(2)
                        s_pass = p1.text_input("Password", type="password", placeholder="Min 8 characters")
                        s_conf = p2.text_input("Confirm password", type="password")
                        agree = st.checkbox("I agree to the Terms of Service and Privacy Policy")
                        go = st.form_submit_button("Create account", type="primary", use_container_width=True)
                    if go:
                        errs = []
                        if not first.strip() or not first.replace(" ", "").isalpha():
                            errs.append("First name must contain letters only.")
                        if not last.strip():
                            errs.append("Last name is required.")
                        if not valid_email(s_email.strip()):
                            errs.append("Enter a valid email address.")
                        if len(s_pass) < 8:
                            errs.append("Password must be at least 8 characters.")
                        if s_pass != s_conf:
                            errs.append("Passwords do not match.")
                        if not agree:
                            errs.append("Please accept the terms to continue.")
                        if errs:
                            for e in errs:
                                st.error(e)
                        else:
                            try:
                                with st.spinner("Creating your account…"):
                                    data = api("POST", "/signUp", body={
                                        "firstName": first.strip(), "lastName": last.strip(),
                                        "emailId": s_email.strip(), "password": s_pass}, auth=False)
                                login_user(data["access_token"], s_email.strip(), first.strip().title())
                            except ApiError as exc:
                                st.error(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# 6. DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        name = st.session_state.user_name or "User"
        st.markdown(
            f'<div class="user-chip"><div class="avatar">{name[:1].upper()}</div>'
            f'<div><b>{name}</b><small>{st.session_state.user_email}</small></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Refresh records", use_container_width=True):
            st.rerun()
        if st.button("Sign out", use_container_width=True):
            logout()
            st.rerun()
        st.divider()
        st.text_input("API URL", key="api_base")
        st.caption("Local backend: http://127.0.0.1:8000")


def dashboard():
    sidebar()

    if st.session_state.flash:
        st.toast(st.session_state.flash)
        st.session_state.flash = None

    try:
        with st.spinner("Loading your students…"):
            students = fetch_all_students()
    except AuthExpired as exc:
        logout(str(exc))
        st.rerun()
    except ApiError as exc:
        st.error("Unable to load data from the backend.")
        st.error(str(exc))
        st.stop()

    by_id = {s["id"]: s for s in students}
    courses = sorted({s["course"] for s in students}, key=str.lower)
    n = len(students)
    avg_marks = sum(s["marks"] for s in students) / n if n else 0
    avg_age = sum(s["age"] for s in students) / n if n else 0
    topper = max(students, key=lambda s: s["marks"]) if n else None

    # ── hero ──
    first_name = (st.session_state.user_name or "there").split()[0]
    st.markdown(
        f'<div class="hero">{greeting()}, <span>{first_name}</span>.</div>'
        f'<div class="sub">{datetime.now():%A, %d %B %Y} — here is your class at a glance.</div>',
        unsafe_allow_html=True,
    )

    cards = [
        ("🎓", "Total students", n, f"Across {len(courses)} course(s)", "hot"),
        ("📈", "Average marks", f"{avg_marks:.1f}", "Out of 100", ""),
        ("🎂", "Average age", f"{avg_age:.1f}", "Years", ""),
        ("🏅", "Top scorer", topper["marks"] if topper else "—", topper["name"] if topper else "No records yet", ""),
    ]
    for col, (icon, label, value, note, cls) in zip(st.columns(4), cards):
        col.markdown(
            f'<div class="stat {cls}"><div class="stat-icon">{icon}</div>'
            f'<div class="stat-label">{label}</div><div class="stat-value">{value}</div>'
            f'<div class="stat-note">{note}</div></div>',
            unsafe_allow_html=True,
        )

    tab_roster, tab_insights, tab_activity = st.tabs(["📚 Student roster", "📊 Insights", "⚡ API activity"])

    # ───────────────────────── ROSTER ─────────────────────────
    with tab_roster:
        st.subheader("Student records")
        st.caption("Add students, browse the roster, or open one student to edit or remove.")

        with st.expander("＋  Add a student", expanded=(n == 0)):
            with st.form("create_student"):
                a, b = st.columns(2)
                sid = a.text_input("Student ID", placeholder="S101")
                name = b.text_input("Full name")
                email = a.text_input("Student email")
                course = b.text_input("Course", placeholder="Computer Science")
                age = a.number_input("Age", 0, 100, 20)
                marks = b.number_input("Marks", 0, 100, 75)
                submitted = st.form_submit_button("Add student", type="primary")

            if submitted:
                payload = {"id": sid.strip(), "name": name.strip(), "age": int(age),
                           "course": course.strip(), "marks": int(marks), "email": email.strip()}
                errors = []
                if not payload["id"]:
                    errors.append("Student ID is required.")
                if not 3 <= len(payload["name"]) <= 50:
                    errors.append("Name must have 3–50 characters.")
                elif not payload["name"].replace(" ", "").isalpha():
                    errors.append("Name can contain only letters and spaces.")
                if not 5 <= len(payload["course"]) <= 30:
                    errors.append("Course must have 5–30 characters.")
                if not valid_email(payload["email"]):
                    errors.append("Enter a valid email.")
                if payload["id"] in by_id:
                    errors.append("You already have a student with this ID.")

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        created = api("POST", "/Create", body=payload)
                        flash(f"Added {created['name']} — grade {created['grade']}")
                        st.session_state.selected_id = created["id"]
                        st.rerun()
                    except ApiError as exc:
                        show_error(exc)

        st.divider()
        with st.container(border=True):
            st.subheader("Browse roster")
            f1, f2, f3 = st.columns([2, 1, 1])
            search = f1.text_input("Search name, email or ID")
            course_filter = f2.selectbox("Course", ["All"] + courses)
            sort_by = f3.selectbox("Sort by", ["ID", "Name", "Age", "Marks"])

            f4, f5, f6 = st.columns([1, 2, 1])
            order = f4.selectbox("Order", ["Ascending", "Descending"])
            marks_range = f5.slider("Marks range", 0, 100, (0, 100))
            page_size = f6.selectbox("Rows per page", [5, 10, 20, 50], index=1)

            rows = list(students)
            if course_filter != "All":
                rows = [s for s in rows if s["course"].lower() == course_filter.lower()]
            if search.strip():
                q = search.strip().lower()
                rows = [s for s in rows if q in s["id"].lower() or q in s["name"].lower() or q in s["email"].lower()]
            rows = [s for s in rows if marks_range[0] <= s["marks"] <= marks_range[1]]

            key = {"ID": "id", "Name": "name", "Age": "age", "Marks": "marks"}[sort_by]
            rows.sort(key=lambda s: s[key].lower() if isinstance(s[key], str) else s[key],
                      reverse=order == "Descending")

            total = len(rows)
            pages = max(1, math.ceil(total / page_size))
            st.session_state.page = max(1, min(st.session_state.page, pages))
            start = (st.session_state.page - 1) * page_size
            visible = rows[start:start + page_size]

            st.caption(f"Showing {len(visible)} of {total} students, sorted by {sort_by.lower()} ({order.lower()}).")
            if visible:
                table = pd.DataFrame([{
                    "ID": s["id"], "Name": s["name"], "Course": s["course"], "Age": s["age"],
                    "Marks": s["marks"], "Grade": s.get("grade", "—"), "Email": s["email"],
                } for s in visible])
                st.dataframe(table, hide_index=True, use_container_width=True)
            elif n == 0:
                st.info("Your roster is empty. Open “Add a student” above to enrol the first one.")
            else:
                st.info("No students match these filters. Try clearing the search or widening the marks range.")

            p1, p2, p3 = st.columns([1, 2, 1])
            if p1.button("← Previous", disabled=st.session_state.page <= 1):
                st.session_state.page -= 1
                st.rerun()
            p2.markdown(f"<div style='text-align:center;padding-top:10px'>Page {st.session_state.page} of {pages}</div>",
                        unsafe_allow_html=True)
            if p3.button("Next →", disabled=st.session_state.page >= pages):
                st.session_state.page += 1
                st.rerun()

        st.divider()
        with st.container(border=True):
            st.subheader("Find a student")
            st.caption("Look up a student by ID to view, update or delete the record.")
            g1, g2 = st.columns([2, 1])
            lookup_id = g1.text_input("Student ID", key="lookup_id", placeholder="S101")
            g2.write("")
            if g2.button("Open profile", use_container_width=True) and lookup_id.strip():
                try:
                    student = api("GET", f"/student/{quote(lookup_id.strip(), safe='')}")
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
            m4.metric("Grade", selected.get("grade", "—"))
            st.caption(f"{selected['course']} · {selected['email']}")

            with st.expander("✎ Update student"):
                with st.form(f"update_{selected['id']}"):
                    u1, u2 = st.columns(2)
                    new_name = u1.text_input("Name", value=selected["name"])
                    new_email = u2.text_input("Email", value=selected["email"])
                    new_course = u1.text_input("Course", value=selected["course"])
                    # backend update requires age > 0 and marks > 0
                    new_age = u2.number_input("Age", 1, 100, max(1, selected["age"]))
                    new_marks = u1.number_input("Marks", 1, 100, max(1, selected["marks"]))
                    save = st.form_submit_button("Save changes", type="primary")

                if save:
                    values = {"name": new_name.strip(), "email": new_email.strip(),
                              "course": new_course.strip(), "age": int(new_age), "marks": int(new_marks)}
                    changes = {k: v for k, v in values.items() if v != selected[k]}
                    errors = []
                    if "name" in changes and (not 3 <= len(changes["name"]) <= 50
                                              or not changes["name"].replace(" ", "").isalpha()):
                        errors.append("Name must be 3–50 letters or spaces.")
                    if "course" in changes and not 5 <= len(changes["course"]) <= 30:
                        errors.append("Course must have 5–30 characters.")
                    if "email" in changes and not valid_email(changes["email"]):
                        errors.append("Enter a valid email.")
                    if errors:
                        for e in errors:
                            st.error(e)
                    elif not changes:
                        st.info("Nothing changed yet.")
                    else:
                        try:
                            updated = api("PUT", f"/Update/{quote(selected['id'], safe='')}", body=changes)
                            flash(f"Updated {updated['name']}")
                            st.rerun()
                        except ApiError as exc:
                            show_error(exc)

            with st.expander("🗑 Delete student"):
                st.warning(f"This permanently removes {selected['name']} from your roster.")
                confirm = st.text_input(f"Type {selected['id']} to confirm", key=f"confirm_{selected['id']}")
                if st.button("Delete permanently", type="primary", disabled=confirm.strip() != selected["id"]):
                    try:
                        deleted = api("DELETE", f"/delete/{quote(selected['id'], safe='')}")
                        flash(f"Deleted {deleted['name']}")
                        st.session_state.selected_id = None
                        st.rerun()
                    except ApiError as exc:
                        show_error(exc)

    # ───────────────────────── INSIGHTS ─────────────────────────
    with tab_insights:
        st.subheader("Academic insights")
        st.caption("Course averages, grade distribution, and how age relates to marks.")
        if not students:
            st.info("Add a few students and your charts will appear here.")
        else:
            df = pd.DataFrame(students)
            if "grade" not in df:
                df["grade"] = "—"
            blue = "#2563eb"
            left, right = st.columns(2)
            with left:
                st.markdown("#### Average marks by course")
                avg = df.groupby("course", as_index=False)["marks"].mean()
                chart = alt.Chart(avg).mark_bar(color=blue, cornerRadiusEnd=6).encode(
                    x=alt.X("marks:Q", title="Average marks"),
                    y=alt.Y("course:N", sort="-x", title=None),
                    tooltip=["course", alt.Tooltip("marks:Q", format=".1f")])
                st.altair_chart(chart, use_container_width=True)
            with right:
                st.markdown("#### Grade distribution")
                counts = df.groupby("grade").size().reset_index(name="students")
                chart = alt.Chart(counts).mark_bar(color="#60a5fa", cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("grade:N", sort=["A+", "A", "B", "C"], title="Grade"),
                    y=alt.Y("students:Q", title="Students"), tooltip=["grade", "students"])
                st.altair_chart(chart, use_container_width=True)
            st.markdown("#### Age vs marks")
            scatter = alt.Chart(df).mark_circle(size=130, opacity=.85).encode(
                x=alt.X("age:Q", title="Age", scale=alt.Scale(zero=False)),
                y=alt.Y("marks:Q", title="Marks"),
                color=alt.Color("course:N", scale=alt.Scale(scheme="blues"), legend=alt.Legend(title="Course")),
                tooltip=["id", "name", "course", "age", "marks", "grade"]).interactive()
            st.altair_chart(scatter, use_container_width=True)

    # ───────────────────────── ACTIVITY ─────────────────────────
    with tab_activity:
        st.subheader("API activity")
        st.caption("Recent requests made by this dashboard, plus a CSV export of your students.")
        if st.session_state.request_log:
            st.dataframe(pd.DataFrame(st.session_state.request_log), hide_index=True, use_container_width=True)
            if st.button("Clear activity"):
                st.session_state.request_log = []
                st.rerun()
        else:
            st.info("No requests yet.")
        st.download_button("Download students CSV", pd.DataFrame(students).to_csv(index=False),
                           file_name="students.csv", mime="text/csv", disabled=not students)


# ─────────────────────────────────────────────────────────────────────────────
# 7. ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.token:
    dashboard()
else:
    auth_page()