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

        # === טיפול בטור 'מסד' ===
        if "מסד" in df.columns:
            # הופך את הטור למספרים נקיים וממיין
            df["מסד"] = pd.to_numeric(df["מסד"], errors='coerce').fillna(0).astype(int)
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

st.markdown('<div class