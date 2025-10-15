# streamlit_app.py
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any
import pathlib
import streamlit as st

# ---------------------------
# App Config
# ---------------------------
st.set_page_config(page_title="🕵️ Sherlock Times", page_icon="🕵️", layout="wide")
APP_TITLE = "🕵️ Sherlock Times – Company, People & Product News Dashboard"

# ---------------------------
# Data Path Auto-Detect
# ---------------------------
# Try both possible locations so it works locally and on Streamlit Cloud
possible_paths = [
    os.path.join(os.path.dirname(__file__), "data"),          # Sherlock_Times/data
    os.path.join(os.path.dirname(__file__), "..", "data")     # ../data
]
DATA_DIR = next((p for p in possible_paths if os.path.exists(p)), possible_paths[0])
DATA_PATH = os.path.join(DATA_DIR, "app_state.json")
USER_FILE = os.path.join(DATA_DIR, "users.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------
# Default Templates
# ---------------------------
DEFAULT_STATE = {
    "meta": {"updated_at": None, "version": "1.1.1"},
    "companies": {}
}
DEFAULT_USERS = {
    "users": [{"username": "admin", "password": "admin123", "role": "admin"}]
}

# ---------------------------
# Load / Save Helpers
# ---------------------------
def _atomic_write_json(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)

def load_state() -> dict:
    """Load app state from JSON, fallback to default."""
    if not os.path.exists(DATA_PATH):
        _atomic_write_json(DATA_PATH, DEFAULT_STATE)
        return DEFAULT_STATE
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # normalize
        if not isinstance(data.get("companies"), dict):
            data["companies"] = {}
        return data
    except Exception as e:
        st.error(f"⚠️ Error reading {DATA_PATH}: {e}")
        return DEFAULT_STATE

def save_state(state: dict):
    state["meta"]["updated_at"] = datetime.utcnow().isoformat()
    _atomic_write_json(DATA_PATH, state)

def load_users() -> dict:
    if not os.path.exists(USER_FILE):
        _atomic_write_json(USER_FILE, DEFAULT_USERS)
        return DEFAULT_USERS
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def verify_user(username: str, password: str):
    for u in load_users().get("users", []):
        if u.get("username") == username and u.get("password") == password:
            return True, u.get("role", "viewer")
    return False, "viewer"

# ---------------------------
# Session Auth
# ---------------------------
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": "viewer", "username": None}

# ---------------------------
# UI Styling
# ---------------------------
st.markdown("""
<style>
.grid-board{display:flex;flex-wrap:wrap;gap:18px;}
.card{flex:1 1 calc(25% - 18px);min-width:280px;max-width:420px;
background:#fff;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.06);
padding:16px;border:1px solid rgba(0,0,0,0.06);}
.card h3{margin:0 0 6px 0;font-size:1.05rem;}
.subtle{color:#6b7280;font-size:0.86rem;margin-bottom:8px;}
.tag{display:inline-block;font-size:0.75rem;padding:2px 8px;margin:3px;
border-radius:999px;background:#f3f4f6;border:1px solid #e5e7eb;}
.small-note{font-size:0.8rem;color:#6b7280;}
.topbar{display:flex;align-items:center;justify-content:space-between;}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Card Generators
# ---------------------------
def company_card(c: dict):
    name = c.get("name", "—")
    location = c.get("location", "")
    cat = c.get("category", "")
    site = c.get("site", "")
    people = c.get("people", [])
    products = c.get("products", [])
    st.markdown(f"""
    <div class="card">
      <h3>{name}</h3>
      <div class="subtle">{cat or "Uncategorized"}{' • ' + location if location else ''}</div>
      <hr>
      <div><b>People:</b> {len(people)}</div>
      <div><b>Products:</b> {len(products)}</div>
      {f'<div class="small-note">🌐 <a href="{site}" target="_blank">{site}</a></div>' if site else ''}
    </div>
    """, unsafe_allow_html=True)

def person_chip(p: dict):
    return f"<span class='tag'>{p.get('name','—')} ({p.get('role','')})</span>"

def product_chip(p: dict):
    return f"<span class='tag'>{p.get('name','—')}</span>"

# ---------------------------
# Header (Title + Top-Right Login)
# ---------------------------
state = load_state()

left, right = st.columns([0.8, 0.2])
with left:
    st.title(APP_TITLE)
    st.caption(f"Last Updated (UTC): {state['meta'].get('updated_at')} • Companies: {len(state.get('companies',{}))}")

with right:
    if not st.session_state.auth["logged_in"]:
        with st.expander("🔐 Admin Login", expanded=False):
            with st.form("login", clear_on_submit=False):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                ok = st.form_submit_button("Login")
            if ok:
                valid, role = verify_user(u, p)
                if valid:
                    st.session_state.auth = {"logged_in": True, "role": role, "username": u}
                    st.success("✅ Logged in")
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials.")
    else:
        st.write(f"👋 {st.session_state.auth['username']} ({st.session_state.auth['role']})")
        if st.button("Logout"):
            st.session_state.auth = {"logged_in": False, "role": "viewer", "username": None}
            st.experimental_rerun()

# ---------------------------
# Tabs
# ---------------------------
tabs = ["🏢 Companies", "🧑‍💼 People", "🧰 Products"]
if st.session_state.auth["logged_in"]:
    tabs.append("⚙️ Admin")
t = st.tabs(tabs)

# ---------------------------
# 🏢 Companies Tab
# ---------------------------
with t[0]:
    st.subheader("Companies")
    comps = state.get("companies", {})
    if not comps:
        st.info("No companies yet. Ask your Admin to add some under the Admin tab.")
    else:
        st.markdown("<div class='grid-board'>", unsafe_allow_html=True)
        for cid, c in comps.items():
            company_card(c)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# 🧑‍💼 People Tab
# ---------------------------
with t[1]:
    st.subheader("People (grouped by company)")
    comps = state.get("companies", {})
    if not comps:
        st.info("No people yet.")
    else:
        for cid, c in comps.items():
            ppl = c.get("people", [])
            if not ppl:
                continue
            with st.expander(f"{c.get('name')} – {len(ppl)}"):
                st.markdown(" ".join(person_chip(p) for p in ppl), unsafe_allow_html=True)

# ---------------------------
# 🧰 Products Tab
# ---------------------------
with t[2]:
    st.subheader("Products (company-wise)")
    comps = state.get("companies", {})
    if not comps:
        st.info("No products yet.")
    else:
        for cid, c in comps.items():
            prods = c.get("products", [])
            if not prods:
                continue
            with st.expander(f"{c.get('name')} – {len(prods)}"):
                st.markdown(" ".join(product_chip(p) for p in prods), unsafe_allow_html=True)

# ---------------------------
# ⚙️ Admin Tab
# ---------------------------
if st.session_state.auth["logged_in"]:
    with t[-1]:
        st.header("⚙️ Admin Panel")
        st.caption("All updates save into data/app_state.json automatically.")
        comps = state.get("companies", {})

        # Add Company
        with st.form("add_company", clear_on_submit=True):
            st.write("### ➕ Add Company")
            cname = st.text_input("Company Name *")
            ccat = st.text_input("Category")
            cloc = st.text_input("Location")
            csite = st.text_input("Website")
            submitted = st.form_submit_button("Add Company")
        if submitted and cname.strip():
            state["companies"][str(uuid.uuid4())] = {
                "name": cname.strip(),
                "category": ccat.strip(),
                "location": cloc.strip(),
                "site": csite.strip(),
                "people": [],
                "products": []
            }
            save_state(state)
            st.success(f"Added {cname}")
            st.experimental_rerun()

        # Delete Company
        st.write("### 🗑 Delete Company")
        if not comps:
            st.info("No companies to delete.")
        else:
            sel = st.selectbox("Select", options=list(comps.keys()), format_func=lambda x: comps[x]["name"])
            if st.button("Delete Selected"):
                removed = comps[sel]["name"]
                comps.pop(sel)
                state["companies"] = comps
                save_state(state)
                st.success(f"Deleted {removed}")
                st.experimental_rerun()
