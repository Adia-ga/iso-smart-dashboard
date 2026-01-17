import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# הגדרות עמוד (חייב להיות ראשון)
# ============================================
st.set_page_config(
    page_title="ISO Smart Dashboard 2.0",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# הגדרות מערכת
# ============================================
SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"
TARGET_DATE = datetime(2026, 6, 1)

# ============================================
# עיצוב CSS - מצב כהה וניאון
# ============================================
st.markdown("""
<style>
    /* רקע כהה לכל האפליקציה */
    .stApp {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    
    /* כותרות ניאון */
    h1, h2, h3 {
        color: #00FFFF !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }
    
    /* תיבת ספירה לאחור */
    .countdown-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
        border: 2px solid #00FFFF;
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
    }
    
    .countdown-number {
        font-size: 4rem;
        color: #00FFFF;
        font-weight: bold;
        text-shadow: 0 0 20px #00FFFF;
        margin: 0;
    }
    
    .countdown-label {
        font-size: 1.2rem;
        color: #FAFAFA;
        opacity: 0.9;
    }

    /* התאמת טבלה למצב כהה */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background-color: #1a1a2e !important;
        border: 1px solid #007FFF;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# חיבור לפיירבייס (עם מנגנון הגנה)
# ============================================
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
        st.error(f"שגיאת התחברות: {e}")
        return None

db = get_db()

# ============================================
# לוגיקה ונתונים
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
            return pd.DataFrame(columns=["משימה", "סטטוס", "עדיפות", "תאריך יעד", "doc_id"])

        # המרת תאריכים בטוחה
        if "תאריך יעד" in df.columns:
            df["תאריך יעד"] = pd.to_datetime(df["תאריך יעד"], errors='coerce').dt.date

        # מילוי ער