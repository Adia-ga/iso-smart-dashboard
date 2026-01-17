import streamlit as st
import pandas as pd
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# הגדרות ראשיות
# ============================================
SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"
TARGET_DATE = datetime(2026, 6, 1)

# ============================================
# הגדרת הדף (חייב להיות בהתחלה)
# ============================================
st.set_page_config(page_title="ISO Dashboard", page_icon="📋", layout="wide")

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
# חיבור למסד הנתונים
# ============================================
@st.cache_resource
def get_db():
    try:
        # בדיקה אם כבר מחובר
        if not firebase_admin._apps:
            # ניסיון 1: חיבור דרך הענן (Secrets)
            if "firebase" in st.secrets:
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
                firebase_admin.initialize_app(cred)
            # ניסיון 2: חיבור מקומי (קובץ במחשב)
            else:
                cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
                firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"תקלת חיבור: {e}")
        return None

db = get_db()

# ============================================
# פונקציות לוגיקה
# ============================================
def get_countdown():
    delta = TARGET_DATE - datetime.now()
    return delta.days, delta.days // 7

def save_task(df_delta):
    # פונקציה לשמירת נתונים
    if db is None: return
    for index, row in df_delta.iterrows():
        data = row.to_dict()
        # המרת תאריכים לטקסט
        if isinstance(data.get("תאריך יעד"), (date, datetime)):
            data["תאריך יעד"] = data["תאריך יעד"].strftime("%Y-%m-%d")
        
        # שמירה (אם יש מזהה מעדכן, אם אין יוצר חדש)
        doc_id = data.pop("doc_id", None)
        if doc_id:
            db.collection(COLLECTION_NAME).document(doc_id).set(data)
        else:
            db.collection(COLLECTION_NAME).add(data)

def load_tasks():
    # טעינת נתונים
    if db is None: return pd.DataFrame()
    docs = db.collection(COLLECTION_NAME).stream()
    items = []
    for doc in docs:
        d = doc.to_dict()
        d["doc_id"] = doc.id
        items.append(d)
    
    if not items: return pd.DataFrame(columns=["משימה", "סטטוס", "עדיפות", "תאריך יעד", "doc_id"])
    return pd.DataFrame(items)

# ============================================
# תצוגה ראשית
# ============================================
st.markdown('<div class="neon-text">📋 ISO Smart Dashboard 2.0</div>', unsafe_allow_html=True)

# שעון עצר
days, weeks = get_countdown()
st.markdown(f"""
<div class="countdown-box">
    <div>נותרו לביקורת ISO/BRC:</div>
    <div class="big-num">{days} ימים</div>
    <div>(כ-{weeks} שבועות)</div>
</div>
""", unsafe_allow_html=True)

# טעינת המשימות
df = load_tasks()

# סטטיסטיקה מהירה
c1, c2, c3 = st.columns(3)
c1.metric("סה\"כ משימות", len(df))
done = len(df[df['סטטוס'] == 'בוצע']) if 'סטטוס' in df.columns else 0
c2.metric("✅ בוצעו", done)
c3.metric("📅 תאריך יעד", "01/06/2026")

st.markdown("### ✏️ רשימת משימות")

# טבלה לעריכה
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    key="editor",
    column_config={
        "doc_id": st.column_config.TextColumn(disabled=True),
        "סטטוס": st.column_config.SelectboxColumn(options=["טרם התחיל", "בטיפול", "בוצע", "נתקע"], required=True),
        "עדיפות": st.column_config.SelectboxColumn(options=["רגיל", "גבוה", "קריטי"], required=True),
        "תאריך יעד": st.column_config.DateColumn(format="DD/MM/YYYY")
    }
)

# כפתור שמירה
if st.button("💾 שמור שינויים לענן", type="primary", use_container_width=True):
    save_task(edited_df)
    st.success("הנתונים נשמרו בהצלחה!")
    st.rerun()