"""
דשבורד חכם לניהול משימות ISO/BRC 2.0
ISO Smart Dashboard 2.0 - Task Management for Audit Preparation
Firestore Edition - Cloud Database Backend
Dark Mode Edition with Neon Color Palette
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# ============================================
# Firebase Imports / ייבוא Firebase
# ============================================

import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# הגדרות כלליות / General Configuration
# ============================================

SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"
TARGET_DATE = datetime(2026, 6, 1)

# כותרות הקובץ / File Headers
HEADERS = ["מס\"ד", "תקן", "קטגוריה", "תת-קטגוריה", "סעיף", "משימה", 
           "תיאור מפורט", "מחלקה", "תאריך יעד", "עדיפות", "סטטוס", "הערות", "משך משוער"]

# אפשרויות סטטוס / Status Options
STATUS_OPTIONS = ["טרם התחיל", "בטיפול", "בוצע", "נתקע"]

# אפשרויות עדיפות / Priority Options
PRIORITY_OPTIONS = ["קריטי", "רגיל", "נמוך"]

# ============================================
# אתחול Firebase / Firebase Initialization
# ============================================

@st.cache_resource
def initialize_firebase():
    """
    מאתחל את Firebase (פעם אחת בלבד).
    """
    try:
        if not firebase_admin._apps:
            # בדיקה: האם אנחנו בענן של Streamlit?
            if "firebase" in st.secrets:
                # Cloud Mode: שימוש במפתח מהכספת
                # יצירת מילון מתוך אובייקט הסודות
                key_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            else:
                # Local Mode: שימוש בקובץ המקומי
                try:
                    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
                    firebase_admin.initialize_app(cred)
                except FileNotFoundError:
                    st.error(f"❌ קובץ '{SERVICE_ACCOUNT_KEY}' לא נמצא! (וודאי שאת במצב מקומי)")
                    return None
        
        return firestore.client()
    
    except Exception as e:
        st.error(f"❌ שגיאה באתחול Firebase: {str(e)}")
        return None

# Initialize Firebase
db = initialize_firebase()

# ============================================
# פונקציות עזר / Helper Functions
# ============================================

def load_data() -> pd.DataFrame:
    try:
        if db is None:
            return pd.DataFrame(columns=HEADERS + ["doc_id"])
        
        docs = db.collection(COLLECTION_NAME).stream()
        records = []
        for doc in docs:
            record = doc.to_dict()
            record["doc_id"] = doc.id
            # ניקוי שדות טכניים
            record.pop("_uploaded_at", None)
            record.pop("_source_row", None)
            records.append(record)
        
        if not records:
            return pd.DataFrame(columns=HEADERS + ["doc_id"])
        
        df = pd.DataFrame(records)
        
        # המרת תאריכים
        if "תאריך יעד" in df.columns:
            def parse_date(val):
                if val is None or pd.isna(val): return None
                try:
                    if isinstance(val, str):
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                            try: return datetime.strptime(val, fmt).date()
                            except: continue
                    return None
                except: return None
            
            df["תאריך יעד"] = df["תאריך יעד"].apply(parse_date)
        
        return df
    
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת נתונים: {str(e)}")
        return pd.DataFrame(columns=HEADERS + ["doc_id"])

def save_data(df: pd.DataFrame) -> bool:
    try:
        if db is None: return False
        
        for index, row in df.iterrows():
            row_data = row.to_dict()
            doc_id = row_data.pop("doc_id", None)
            
            # המרת תאריך למחרוזת
            if "תאריך יעד" in row_data and isinstance(row_data["תאריך יעד"], (date, datetime)):
                row_data["תאריך יעד"] = row_data["תאריך יעד"].strftime("%Y-%m-%d")
            
            cleaned_data = {k: (v.item() if hasattr(v, 'item') else v) for k, v in row_data.items() if not pd.isna(v)}
            cleaned_data["_updated_at"] = firestore.SERVER_TIMESTAMP
            
            if doc_id and doc_id != "":
                db.collection(COLLECTION_NAME).document(doc_id).set(cleaned_data)
            else:
                db.collection(COLLECTION_NAME).add(cleaned_data)
        return True
    except Exception as e:
        st.error(f"❌ שגיאה בשמירה: {str(e)}")
        return False

def get_countdown() -> dict:
    delta = TARGET_DATE - datetime.now()
    return {"days": delta.days, "weeks": delta.days // 7, "months": delta.days // 30}

# ============================================
# הגדרת הדף / Page Configuration
# ============================================

st.set_page_config(page_title="ISO Smart Dashboard", page_icon="📋", layout="wide")

# ============================================
# עיצוב CSS / Styling
# ============================================

st.markdown("""
<style>
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    .main-title { text-align: center; color: #00FFFF !important; font-size: 3rem; text-shadow: 0 0 10px #00FFFF; }
    .countdown-container { background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); border: 2px solid #00FFFF; border-radius: 20px; padding: 2rem; text-align: center; margin-bottom: 2rem; }
    .countdown-number { font-size: 4rem; color: #00FFFF !important; font-weight: bold; }
    [data-testid="stMetricValue"] { color: #FAFAFA !important; }
</style>
""", unsafe_allow_html=True)

# ============================================
# כותרת וספירה לאחור / Header & Countdown
# ============================================

st.markdown('<h1 class="main-title">📋 ISO Smart Dashboard 2.0</h1>', unsafe_allow_html=True)

countdown = get_