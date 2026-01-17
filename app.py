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
    layout="wide"
)

# ============================================
# הגדרות מערכת
# ============================================
SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"
TARGET_DATE = datetime(2026, 6, 1)

# ============================================
# עיצוב CSS
# ============================================
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    h1, h2, h3 {
        color: #00FFFF !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }
    .countdown-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
        border: 2px solid #00FFFF;
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    .countdown-number {
        font-size: 4rem;
        color: #00FFFF;
        font-weight: bold;
    }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background-color: #1a1a2e !important;
    }
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
# פונקציות לוגיקה
# ============================================
def get_countdown():
    delta = TARGET_DATE - datetime.now()
    return delta.days, delta.days // 7

def load_tasks():
    # בדיקה שקיים חיבור
    if db is None: 
        return pd.DataFrame()
    
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

        # המרות וניקוי
        if "תאריך יעד" in df.columns:
            df["תאריך יעד"] = pd.to_datetime(df["תאריך יעד"], errors='coerce').dt.date

        if "סטטוס" not in df.columns: df["סטטוס"] = "טרם התחיל"
        if "עדיפות" not in df.columns: df["עדיפות"] = "רגיל"
        
        return df.fillna("")
        
    except Exception as e:
        # זה הבלוק שהיה חסר קודם
        st.error(f"שגיאה בטעינת נתונים: {e}")
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
# תצוגה ראשית
# ============================================

st.markdown('<h1 style="text-align:center;">📋 ISO Smart Dashboard 2.0</h1>', unsafe_allow_html=True)

# שעון
days, weeks = get_countdown()
st.markdown(f"""
<div class="countdown-box">
    <p>🎯 נותרו לביקורת ISO/BRC:</p>
    <p class="countdown-number">{days}</p>
    <p>ימים (כ-{weeks} שבועות)</p>
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
    c3.metric("🚨 לטיפול מיידי", critical)
    
    st.divider()

    # גרף
    st.markdown("### 📊 תמונת מצב")
    if 'סטטוס' in df.columns:
        status_counts = df['סטטוס'].value_counts().reset_index()
        status_counts.columns = ['סטטוס', 'כמות']
        
        fig = px.pie(status_counts, values='כמות', names='סטטוס', 
                     color_discrete_sequence=["#00FFFF", "#FF00FF", "#39FF14", "#FFFF00"],
                     hole=0.4)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                          font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# טבלה
st.markdown("### ✏️ רשימת משימות")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    key="editor",
    column_config={
        "doc_id": st.column_config.TextColumn(disabled=True),
        "סטטוס": st.column_config.SelectboxColumn(
            options=["טרם התחיל", "בטיפול", "בוצע", "נתקע"],
            required=True
        ),
        "עדיפות": st.column_config.SelectboxColumn(
            options=["רגיל", "גבוה", "קריטי"],
            required=True
        ),
        "תאריך יעד": st.column_config.DateColumn(format="DD/MM/YYYY")
    }
)

if st.button("💾 שמור שינויים לענן", type="primary", use_container_width=True):
    if save_task(edited_df):
        st.success("✅ השינויים נשמרו בהצלחה!")
        st.rerun()

st.markdown("---")
st.markdown('<p style="text-align:center; color:#007FFF;">ISO Smart Dashboard | Powered by Firebase</p>', unsafe_allow_html=True)