# streamlit_app.py

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Tuple

import streamlit as st

# Optional imports from your older stack; keeping these so your env doesn't break
# Remove if you truly don't use them anywhere else.
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
except Exception:
    analyzer = None

# ---------------------------
# App Config
# ---------------------------
st.set_page_config(page_title="🕵️ Sherlock Times", page_icon="🕵️", layout="wide")

APP_TITLE = "🕵️ Sherlock Times – Company, People & Product News Dashboard"

DATA_DIR = "data"
DATA_PATH = os.path.join(DATA_DIR, "app_state.json")
USER_FILE = os.path.join(DATA_DIR, "users.json")

# ---------------------------
# Ensure data directory/files
# ---------------------------
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_STATE = {
    "meta": {"updated_at": None, "version": "1.1.0"},
    "companies": {
        # "company_id": {
        #     "name": "Acme Corp",
        #     "site": "https://acme.example.com",
        #     "category": "Technology",
        #     "people": [
        #         {"id": "uuid", "name": "Jane Doe", "role": "CTO", "link": "https://..."}
        #     ],
        #     "products": [
        #         {"id": "uuid", "name": "RoadRunner 2.0", "desc": "High-speed...", "link": "https://...", "tags": ["ai","cloud"]}
        #     ]
        # }
    }
}

DEFAULT_USERS = {
    "users": [
        # 🔐 Default admin (change this in users.json after first run)
        {"username": "admin", "password": "admin123", "role": "admin"}
    ]
}

def _atomic_write_json(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)

def load_state() -> dict:
    if not os.path.exists(DATA_PATH):
        state = DEFAULT_STATE.copy()
        state["meta"]["updated_at"] = datetime.utcnow().isoformat()
        _atomic_write_json(DATA_PATH, state)
        return state
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict):
    state["meta"]["updated_at"] = datetime.utcnow().isoformat()
    _atomic_write_json(DATA_PATH, state)

def load_users() -> dict:
    if not os.path.exists(USER_FILE):
        _atomic_write_json(USER_FILE, DEFAULT_USERS)
        return DEFAULT_USERS
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def verify_user(username: str, password: str) -> Tuple[bool, str]:
    users = load_users().get("users", [])
    for u in users:
        if u.get("username") == username and u.get("password") == password:
            return True, u.get("role", "viewer")
    return False, "viewer"

# ---------------------------
# UI Helpers (Cards & Layout)
# ---------------------------
CARD_CSS = """
<style>
.grid-board {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: stretch;
  gap: 18px;
}
.card {
  flex: 1 1 calc(25% - 18px);
  min-width: 280px;
  max-width: 420px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.06);
  padding: 16px;
  border: 1px solid rgba(0,0,0,0.06);
}
.card h3 {
  margin: 0 0 6px 0;
  font-size: 1.05rem;
}
.card .subtle {
  color: #6b7280;
  font-size: 0.86rem;
  margin-bottom: 8px;
}
.tag {
  display: inline-block;
  font-size: 0.75rem;
  padding: 2px 8px;
  margin-right: 6px;
  margin-bottom: 6px;
  border-radius: 999px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}
.kv {
  font-size: 0.88rem;
  margin-top: 8px;
}
.kv span {
  color: #374151;
}
.section-title {
  font-weight: 700;
  margin: 10px 0 4px 0;
}
hr.sep {
  border: none;
  border-top: 1px dashed #e5e7eb;
  margin: 12px 0;
}
.small-note {
  font-size: 0.8rem;
  color: #6b7280;
}
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

def company_card(c: dict):
    name = c.get("name", "—")
    site = c.get("site") or ""
    cat = c.get("category") or "Uncategorized"
    people = c.get("people", [])
    products = c.get("products", [])
    st.markdown(
        f"""
        <div class="card">
            <h3>{name}</h3>
            <div class="subtle">{cat}</div>
            <hr class="sep" />
            <div class="section-title">People</div>
            <div class="kv"><span>{len(people)}</span> listed</div>
            <div class="section-title" style="margin-top:10px;">Products</div>
            <div class="kv"><span>{len(products)}</span> listed</div>
            {'<hr class="sep" />' if site else ''}
            {f'<div class="small-note">🌐 <a href="{site}" target="_blank">{site}</a></div>' if site else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

def person_chip(p: dict) -> str:
    nm = p.get("name","—")
    rl = p.get("role","")
    ln = p.get("link","")
    tip = f"{nm} – {rl}" if rl else nm
    if ln:
        return f'<span class="tag"><a href="{ln}" target="_blank" title="{tip}">{nm}</a></span>'
    return f'<span class="tag" title="{tip}">{nm}</span>'

def product_chip(p: dict) -> str:
    nm = p.get("name","—")
    desc = p.get("desc","")
    ln = p.get("link","")
    tip = f"{nm} – {desc[:80]}{'…' if len(desc)>80 else ''}"
    if ln:
        return f'<span class="tag"><a href="{ln}" target="_blank" title="{tip}">{nm}</a></span>'
    return f'<span class="tag" title="{tip}">{nm}</span>'

# ---------------------------
# Session Auth
# ---------------------------
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": "viewer", "username": None}

def do_login():
    with st.sidebar:
        st.markdown("### 🔐 Admin Login")
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", value="", autocomplete="username")
            p = st.text_input("Password", value="", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Login")
        if submitted:
            ok, role = verify_user(u, p)
            if ok:
                st.session_state.auth = {"logged_in": True, "role": role, "username": u}
                st.success("Logged in successfully.")
            else:
                st.error("Invalid credentials.")

def do_logout():
    with st.sidebar:
        if st.session_state.auth.get("logged_in"):
            if st.button("Logout"):
                st.session_state.auth = {"logged_in": False, "role": "viewer", "username": None}
                st.info("Logged out.")

# ---------------------------
# App Title / Header
# ---------------------------
st.title(APP_TITLE)
meta_col1, meta_col2, meta_col3 = st.columns([2,1,1])

state = load_state()
updated_at = state.get("meta",{}).get("updated_at")
with meta_col1:
    st.caption(f"Last Updated (UTC): {updated_at if updated_at else '—'}")
with meta_col2:
    st.caption(f"Companies: {len(state.get('companies',{}))}")
with meta_col3:
    if st.session_state.auth.get("logged_in"):
        st.caption(f"Role: {st.session_state.auth.get('role','viewer')}")

# Sidebar auth
do_login()
do_logout()

# ---------------------------
# Tabs (Admin only visible when logged in)
# ---------------------------
base_tabs = ["🏢 Companies", "🧑‍💼 People", "🧰 Products"]
if st.session_state.auth.get("logged_in"):
    tabs = base_tabs + ["⚙️ Admin"]
else:
    tabs = base_tabs

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
        st.markdown('<div class="grid-board">', unsafe_allow_html=True)
        for cid, c in comps.items():
            company_card(c)
        st.markdown('</div>', unsafe_allow_html=True)

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
            with st.expander(f"{c.get('name','—')} — {len(ppl)}"):
                chips = " ".join([person_chip(p) for p in ppl])
                st.markdown(chips, unsafe_allow_html=True)

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
            with st.expander(f"{c.get('name','—')} — {len(prods)}"):
                chips = " ".join([product_chip(p) for p in prods])
                st.markdown(chips, unsafe_allow_html=True)

# ---------------------------
# ⚙️ Admin Tab (only if logged in)
# ---------------------------
if st.session_state.auth.get("logged_in"):
    with t[-1]:
        st.markdown("### Admin – Manage Companies, People & Products")
        st.caption("All changes persist into **data/app_state.json** and are visible to everyone.")

        admin_tabs = st.tabs(["➕ Add / 🗑 Delete Company", "👥 Manage People", "🧩 Manage Products"])

        # -----------------------
        # Company Management
        # -----------------------
        with admin_tabs[0]:
            st.markdown("#### Add a Company")
            with st.form("add_company_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    cname = st.text_input("Company Name *")
                    ccat = st.text_input("Category", placeholder="Technology / FinTech / Retail ...")
                with col2:
                    csite = st.text_input("Website (URL)", placeholder="https://example.com")

                submitted = st.form_submit_button("Add Company")
            if submitted:
                if not cname.strip():
                    st.error("Company Name is required.")
                else:
                    # Prevent duplicates by name (case-insensitive)
                    exists = None
                    for cid, c in state["companies"].items():
                        if c.get("name","").strip().lower() == cname.strip().lower():
                            exists = cid
                            break
                    if exists:
                        st.warning(f"Company '{cname}' already exists.")
                    else:
                        cid = str(uuid.uuid4())
                        state["companies"][cid] = {
                            "name": cname.strip(),
                            "site": csite.strip(),
                            "category": ccat.strip(),
                            "people": [],
                            "products": []
                        }
                        save_state(state)
                        st.success(f"Company '{cname}' added.")

            st.markdown("---")
            st.markdown("#### Delete a Company")
            comps = state.get("companies", {})
            if not comps:
                st.info("No companies to delete.")
            else:
                # Show by name sorted
                options = [(c.get("name","—"), cid) for cid, c in comps.items()]
                options = sorted(options, key=lambda x: x[0].lower())
                labels = [o[0] for o in options]
                values = [o[1] for o in options]
                sel = st.selectbox("Select Company to delete", options=values, format_func=lambda cid: next((n for n, i in options if i==cid), "—"))
                if st.button("Delete Company", type="primary"):
                    removed_name = state["companies"].get(sel, {}).get("name","—")
                    state["companies"].pop(sel, None)
                    save_state(state)
                    st.success(f"Company '{removed_name}' deleted.")

        # -----------------------
        # People Management
        # -----------------------
        with admin_tabs[1]:
            comps = state.get("companies", {})
            if not comps:
                st.info("Add a company first.")
            else:
                st.markdown("#### Add Person")
                options = [(c.get("name","—"), cid) for cid, c in comps.items()]
                options = sorted(options, key=lambda x: x[0].lower())
                labels = [o[0] for o in options]
                values = [o[1] for o in options]
                colA, colB = st.columns(2)
                with colA:
                    sel_cid = st.selectbox("Company *", options=values, format_func=lambda cid: next((n for n, i in options if i==cid), "—"), key="people_company_sel_add")
                with colB:
                    pass  # spacing

                with st.form("add_person_form", clear_on_submit=True):
                    pcol1, pcol2, pcol3 = st.columns(3)
                    with pcol1:
                        pname = st.text_input("Name *")
                    with pcol2:
                        prole = st.text_input("Role/Title", placeholder="CTO, Head of Product, ...")
                    with pcol3:
                        plink = st.text_input("Profile Link", placeholder="https://linkedin.com/in/...")

                    submitted = st.form_submit_button("Add Person")
                if submitted:
                    if not pname.strip():
                        st.error("Person name is required.")
                    else:
                        person = {"id": str(uuid.uuid4()), "name": pname.strip(), "role": prole.strip(), "link": plink.strip()}
                        state["companies"][sel_cid].setdefault("people", []).append(person)
                        save_state(state)
                        st.success(f"Added '{pname}' to {state['companies'][sel_cid]['name']}.")

                st.markdown("---")
                st.markdown("#### Delete Person")
                sel_cid2 = st.selectbox("Company", options=values, format_func=lambda cid: next((n for n, i in options if i==cid), "—"), key="people_company_sel_del")
                ppl = state["companies"][sel_cid2].get("people", [])
                if not ppl:
                    st.info("No people yet for this company.")
                else:
                    p_opts = [(f"{p.get('name','—')} — {p.get('role','')}", p.get("id")) for p in ppl]
                    sel_pid = st.selectbox("Select person to delete", options=[pid for _, pid in p_opts], format_func=lambda pid: next((label for label, _id in p_opts if _id==pid), "—"))
                    if st.button("Delete Person", key="delete_person_btn", type="primary"):
                        before = len(ppl)
                        ppl = [p for p in ppl if p.get("id") != sel_pid]
                        state["companies"][sel_cid2]["people"] = ppl
                        save_state(state)
                        st.success("Person deleted.")

        # -----------------------
        # Products Management
        # -----------------------
        with admin_tabs[2]:
            comps = state.get("companies", {})
            if not comps:
                st.info("Add a company first.")
            else:
                st.markdown("#### Add Product")
                options = [(c.get("name","—"), cid) for cid, c in comps.items()]
                options = sorted(options, key=lambda x: x[0].lower())
                values = [o[1] for o in options]

                sel_cid_p = st.selectbox("Company *", options=values, format_func=lambda cid: next((n for n, i in options if i==cid), "—"), key="product_company_sel_add")

                with st.form("add_product_form", clear_on_submit=True):
                    pr1, pr2 = st.columns([2,1])
                    with pr1:
                        pname = st.text_input("Product Name *")
                        pdesc = st.text_area("Short Description", placeholder="One-liner or 2-3 lines about the product.")
                    with pr2:
                        plink = st.text_input("Product Link", placeholder="https://...")
                        ptags = st.text_input("Tags (comma separated)", placeholder="ai, cloud, analytics")
                    submitted = st.form_submit_button("Add Product")
                if submitted:
                    if not pname.strip():
                        st.error("Product name is required.")
                    else:
                        tags = [t.strip() for t in ptags.split(",") if t.strip()] if ptags else []
                        prod = {
                            "id": str(uuid.uuid4()),
                            "name": pname.strip(),
                            "desc": pdesc.strip(),
                            "link": plink.strip(),
                            "tags": tags
                        }
                        state["companies"][sel_cid_p].setdefault("products", []).append(prod)
                        save_state(state)
                        st.success(f"Product '{pname}' added to {state['companies'][sel_cid_p]['name']}.")

                st.markdown("---")
                st.markdown("#### Delete Product")
                sel_cid_pd = st.selectbox("Company", options=values, format_func=lambda cid: next((n for n, i in options if i==cid), "—"), key="product_company_sel_del")
                prods = state["companies"][sel_cid_pd].get("products", [])
                if not prods:
                    st.info("No products yet for this company.")
                else:
                    p_opts = [(p.get("name","—"), p.get("id")) for p in prods]
                    sel_prid = st.selectbox("Select product to delete", options=[pid for _, pid in p_opts], format_func=lambda pid: next((label for label, _id in p_opts if _id==pid), "—"))
                    if st.button("Delete Product", key="delete_product_btn", type="primary"):
                        prods = [p for p in prods if p.get("id") != sel_prid]
                        state["companies"][sel_cid_pd]["products"] = prods
                        save_state(state)
                        st.success("Product deleted.")
