import streamlit as st
import pandas as pd
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# הגדרות מערכת
# ============================================
st.set_page_config(page_title="ISO Dashboard", page_icon="📋", layout="wide")

SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"
TARGET_DATE = datetime(2026, 6, 1)

# עיצוב
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    .neon-text { color: #00FFFF; text-shadow: 0 0 10px #00FFFF; text-align: center; font-size: 3em; font-weight: bold; }
    .countdown-box { border: 2px solid #00FFFF; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; background: #1a1a2e; }
    .big-num { font-size: 3em; color: #00FFFF; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============================================
# חיבור לפיירבייס
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
# פונקציות עזר
# ============================================
def get_countdown():
    delta = TARGET_DATE - datetime.now()
    return delta.days, delta.days // 7

def load_tasks():
    # פונקציה חכמה לטעינת נתונים ומניעת קריסות
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

        # המרת תאריכים בטוחה (מונע קריסה אם התאריך לא תקין)
        if "תאריך יעד" in df.columns:
            df["תאריך יעד"] = pd.to_datetime(df["תאריך יעד"], errors='coerce').dt.date

        # מילוי ערכים חסרים כדי למנוע שגיאות
        if "סטטוס" not in df.columns: df["סטטוס"] = "טרם התחיל"
        if "עדיפות" not in df.columns: df["עדיפות"] = "רגיל"
        
        df = df.fillna("") # ממלא חורים ריקים
        return df
        
    except Exception as e:
        st.error(f"שגיאה בטעינת הנתונים: {e}")
        return pd.DataFrame()

def save_task(edited_df):
    if db is None: return
    for index, row in edited_df.iterrows():
        data = row.to_dict()
        doc_id = data.pop("doc_id", None)
        
        # המרת תאריך לפורמט שהענן אוהב
        if isinstance(data.get("תאריך יעד"), (date, datetime)):
            data["תאריך יעד"] = data["תאריך יעד"].strftime("%Y-%m-%d")
            
        if doc_id and len(str(doc_id)) > 5: # עדכון קיים
            db.collection(COLLECTION_NAME).document(doc_id).set(data, merge=True)
        else: # יצירה חדשה
            db.collection(COLLECTION_NAME).add(data)

# ============================================
# תצוגה ראשית
# ============================================
st.markdown('<div class="neon-text">📋 ISO Smart Dashboard</div>', unsafe_allow_html=True)

# שעון
days, weeks = get_countdown()
st.markdown(f"""
<div class="countdown-box">
    <div>ימים לביקורת:</div>
    <div class="big-num">{days}</div>
</div>
""", unsafe_allow_html=True)

# טעינת נתונים
df = load_tasks()

# הצגת נתונים
if not df.empty:
    st.markdown("### ✏️ רשימת המשימות שלך מהענן")
    
    # טבלה בטוחה - ללא הגדרות נוקשות שגורמות לקריסה
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor",
        column_config={
             "doc_id": st.column_config.TextColumn(disabled=True),
             "תאריך יעד": st.column_config.DateColumn(format="DD/MM/YYYY")
        }
    )

    if st.button("💾 שמור שינויים", type="primary", use_container_width=True):
        save_task(edited_df)
        st.success("הנתונים נשמרו!")
        st.rerun()
else:
    st.info("התחברנו לפיירבייס, אבל הטבלה ריקה כרגע. נסי להוסיף שורה חדשה.")