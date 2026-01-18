import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# --- הגדרות עמוד ---
st.set_page_config(page_title="ISO Smart Dashboard", page_icon="📋", layout="wide")

# --- עיצוב CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    .main-title { text-align: center; color: #00FFFF !important; font-size: 3rem; font-weight: bold; text-shadow: 0 0 10px #00FFFF; }
    .countdown-box { background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); border: 2px solid #00FFFF; border-radius: 20px; padding: 20px; text-align: center; margin-bottom: 20px; }
    .cnt-num { font-size: 4rem; font-weight: bold; color: #00FFFF; }
    [data-testid="stMetricValue"] { color: #00FFFF !important; }
    [data-testid="stMetricLabel"] { color: #FAFAFA !important; }
    [data-testid="stMetric"] { background-color: #1a1a2e; border: 1px solid #FF00FF; }
</style>
""", unsafe_allow_html=True)

# --- חיבור Firebase ---
key_path = "serviceAccountKey.json"
collection_name = "tasks"
target_date = datetime(2026, 6, 1)

@st.cache_resource
def get_db():
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
                firebase_admin.initialize_app(cred)
            else:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

db = get_db()

# --- לוגיקה ---
def load_data():
    if db is None: return pd.DataFrame()
    try:
        docs = db.collection(collection_name).stream()
        data = [{"doc_id": doc.id, **doc.to_dict()} for doc in docs]
        df = pd.DataFrame(data)
        
        if df.empty:
            return pd.DataFrame(columns=["מסד", "משימה", "סטטוס", "עדיפות", "תאריך יעד", "doc_id"])

        if "מסד" in df.columns:
            df["מסד"] = pd.to_numeric(df["מסד"], errors='coerce').fillna(0).astype(int)
            df = df.sort_values(by="מסד", ascending=True)
        else:
            df["מסד"] = 0

        if "תאריך יעד" in df.columns:
            df["תאריך יעד"] = pd.to_datetime(df["תאריך יעד"], errors='coerce').dt.date

        return df.fillna("")
    except:
        return pd.DataFrame()

def save_data(edited_df):
    if db is None: return
    try:
        for i, row in edited_df.iterrows():
            d = row.to_dict()
            doc_id = d.pop("doc_id", None)
            if isinstance(d.get("תאריך יעד"), (date, datetime)):
                d["תאריך יעד"] = d["תאריך יעד"].strftime("%Y-%m-%d")
            
            clean = {k: v for k, v in d.items() if v != "" and v is not None}
            clean["_updated_at"] = firestore.SERVER_TIMESTAMP
            
            if doc_id and len(str(doc_id)) > 5:
                db.collection(collection_name).document(doc_id).set(clean, merge=True)
            else:
                db.collection(collection_name).add(clean)
        return True
    except:
        return False

# --- תצוגה ---
st.markdown('<div class="main-title">ISO Smart Dashboard</div>', unsafe_allow_html=True)

delta = target_date - datetime.now()
st.markdown(f"""
<div class="countdown-box">
    <div style="color:#FAFAFA;">🎯 ימים לביקורת:</div>
    <div class="cnt-num">{delta.days}</div>
</div>
""", unsafe_allow_html=True)

df = load_data()

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("📋 סה\"כ", len(df))
    done_count = len(df[df['סטטוס'].astype(str).str.contains('בוצע')]) if 'סטטוס' in df.columns else 0
    c2.metric("✅ בוצעו", done_count)
    crit_count = len(df[df['עדיפות'] == 'קריטי']) if 'עדיפות' in df.columns else 0
    c3.metric("🚨 קריטי", crit_count)
    
    st.divider()
    
    if 'סטטוס' in df.columns:
        counts = df['סטטוס'].value_counts().reset_index()
        counts.columns = ['סטטוס', 'כמות']
        fig = px.pie(counts, values='כמות', names='סטטוס', hole=0.4,
                     color_discrete_sequence=["#00FFFF", "#FF00FF", "#39FF14", "#FFFF00"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown("### ✏️ רשימת משימות (ממוין לפי מסד)")

cols = ["מסד", "משימה", "סטטוס", "עדיפות", "תאריך יעד"]
final_cols = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]

edited = st.data_editor(
    df[final_cols],
    num_rows="dynamic",
    use_container_width=True,
    key="editor",
    column_config={
        "doc_id": st.column_config.TextColumn(disabled=True),