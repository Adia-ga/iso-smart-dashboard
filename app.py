import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# הגדרות עמוד
# ============================================
st.set_page_config(
    page_title="ISO Smart Dashboard 2.0",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# עיצוב CSS - ניאון וסייברפאנק
# ============================================
st.markdown("""
<style>
    /* רקע כללי */
    .stApp {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    
    /* כותרות */
    .main-title {
        text-align: center;
        color: #00FFFF !important;
        font-size: 3.5rem;
        font-weight: bold;
        text-shadow: 0 0 10px #00FFFF;
    }
    
    /* קופסת ספירה */
    .countdown-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 2px solid #00FFFF;
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        margin-bottom: 30px;
    }
    .countdown-number {
        font-size: 4rem;
        font-weight: bold;
        color: #00FFFF !important;
    }
    
    /* עיצוב מדדים */
    [data-testid="stMetricValue"] { color: #00FFFF !important; }
    [data-testid="stMetricLabel"] { color: #FAFAFA !important; }
    [data-testid="stMetric"] {
        background-color: #1a1a2e;
        border: 1px solid #FF00FF;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# חיבור Firebase
# ============================================
SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"
TARGET_DATE = datetime(2026, 6, 1)

@st.cache_resource
def get_db():
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
                firebase_admin.initialize_app(cred)
            else:
                cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
                firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"שגיאת חיבור: {e}")
        return None

db = get_db()

# ============================================
# לוגיקה
# ============================================
def get_countdown():
    delta = TARGET_DATE - datetime.now()
    return delta.days, delta.days // 7

def load_tasks():
    if db is None: return pd.DataFrame()
    try:
        docs = db.collection(COLLECTION_NAME).stream()
        items = []
        for doc in docs:
            d = doc.to_dict()
            d["doc_id"] = doc.id
            items.append(d)
        
        df = pd.DataFrame(items)
        
        if df.empty:
            return pd.DataFrame(columns=["מסד", "משימה", "סטטוס", "עדיפות", "תאריך יעד", "doc_id"])

        # === טיפול בטור 'מסד' למיון ===
        if "מסד" in df.columns:
            # הופך את הטור למספרים נקיים
            df["מסד"] = pd.to_numeric(df["מסד"], errors='coerce').fillna(0).astype(int)
            # מיון לפי מסד
            df = df.sort_values(by="מסד", ascending=True)
        else:
            df["מסד"] = 0

        # המרת תאריכים
        if "תאריך יעד" in df.columns:
            df["תאריך יעד"] = pd.to_datetime(df["תאריך יעד"], errors='coerce').dt.date
        
        # מילוי חוסרים
        if "סטטוס" not in df.columns: df["סטטוס"] = "טרם התחיל"
        if "עדיפות" not in df.columns: df["עדיפות"] = "רגיל"
        
        return df.fillna("")
    except Exception as e:
        st.error(f"שגיאה בטעינה: {e}")
        return pd.DataFrame()

def save_task(edited_df):
    if db is None: return
    try:
        for index, row in edited_df.iterrows():
            data = row.to_dict()
            doc_id = data.pop("doc_id", None)
            
            if isinstance(data.get("תאריך יעד"), (date, datetime)):
                data["תאריך יעד"] = data["תאריך יעד"].strftime("%Y-%m-%d")
            
            clean_data = {k: v for k, v in data.items() if v != "" and v is not None}
            clean_data["_updated_at"] = firestore.SERVER_TIMESTAMP
                
            if doc_id and len(str(doc_id)) > 5:
                db.collection(COLLECTION_NAME).document(doc_id).set(clean_data, merge=True)
            else:
                db.collection(COLLECTION_NAME).add(clean_data)
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירה: {e}")
        return False

# ============================================
# UI - תצוגה
# ============================================

st.markdown('<div class="main-title">ISO Smart Dashboard</div>', unsafe_allow_html=True)

# שעון
days, weeks = get_countdown()
st.markdown(f"""
<div class="countdown-container">
    <div style="font-size:1.2rem; color:#FAFAFA;">🎯 זמן לביקורת:</div>
    <div class="countdown-number">{days}</div>
    <div style="font-size:1.2rem; color:#FAFAFA;">ימים</div>
</div>
""", unsafe_allow_html=True)

# טעינה
df = load_tasks()

# מדדים
if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("📋 סה\"כ", len(df))
    done = len(df[df['סטטוס'].astype(str).str.contains('בוצע')]) if 'סטטוס' in df.columns else 0
    c2.metric("✅ בוצעו", done)
    critical = len(df[df['עדיפות'] == 'קריטי']) if 'עדיפות' in df.columns else 0
    c3.metric("🚨 קריטי", critical)
    
    st.divider()

    # גרף (כאן הייתה השגיאה קודם - תוקן)
    st.markdown("### 📊 תמונת מצב")
    if 'סטטוס' in df.columns:
        status_counts = df['סטטוס'].value_counts().reset_index()
        status_counts.columns = ['סטטוס', 'כמות']
        
        fig = px.pie(
            status_counts, 
            values='כמות', 
            names='סטטוס', 
            color_discrete_sequence=["#00FFFF", "#FF00FF", "#39FF14", "#FFFF00"],
            hole=0.4
        )
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)", 
            font=dict(color="white")
        )
        
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# טבלה
st.markdown("### ✏️ רשימת המשימות")

# סידור עמודות - מסד ראשון
cols = ["מסד", "משימה", "סטטוס", "עדיפות", "תאריך יעד"]
existing = [c for c in cols if c in df.columns]
rest = [c for