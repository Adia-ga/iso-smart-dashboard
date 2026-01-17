import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# הגדרות עמוד (חובה שורה ראשונה)
# ============================================
st.set_page_config(
    page_title="ISO Smart Dashboard 2.0",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# עיצוב CSS מתקדם - ניאון וסייברפאנק
# ============================================
st.markdown("""
<style>
    /* רקע כללי */
    .stApp {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    
    /* כותרת ראשית זוהרת */
    .main-title {
        text-align: center;
        color: #00FFFF !important;
        font-size: 3.5rem;
        font-weight: bold;
        text-shadow: 0 0 10px #00FFFF, 0 0 20px #00FFFF;
        margin-bottom: 0px;
    }
    
    .sub-title {
        text-align: center;
        color: #FF00FF !important;
        font-size: 1.2rem;
        margin-bottom: 30px;
        text-shadow: 0 0 5px #FF00FF;
    }
    
    /* קופסת ספירה לאחור */
    .countdown-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 2px solid #00FFFF;
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
        margin-bottom: 30px;
    }
    
    .countdown-number {
        font-size: 4rem;
        font-weight: bold;
        color: #00FFFF !important;
        text-shadow: 0 0 20px #00FFFF;
        line-height: 1;
    }
    
    .countdown-label {
        font-size: 1.2rem;
        color: #FAFAFA;
        opacity: 0.9;
    }
    
    /* עיצוב כרטיסיות מדדים (KPI) */
    [data-testid="stMetric"] {
        background-color: #1a1a2e;
        border: 1px solid #FF00FF;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 0 10px rgba(255, 0, 255, 0.2);
    }
    [data-testid="stMetricLabel"] { color: #FAFAFA !important; }
    [data-testid="stMetricValue"] { color: #00FFFF !important; }

    /* כפתורים */
    .stButton > button {
        background: linear-gradient(90deg, #00FFFF 0%, #007FFF 100%);
        color: #000000 !important;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 0 15px #00FFFF;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# הגדרות מערכת וחיבור Firebase
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
        st.error(f"שגיאת חיבור למסד הנתונים: {e}")
        return None

db = get_db()

# ============================================
# לוגיקה (פונקציות)
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

        # ניקוי והמרות
        if "תאריך יעד" in df.columns:
            df["תאריך יעד"] = pd.to_datetime(df["תאריך יעד"], errors='coerce').dt.date
        
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
            
            # תיקון תאריכים
            if isinstance(data.get("תאריך יעד"), (date, datetime)):
                data["תאריך יעד"] = data["תאריך יעד"].strftime("%Y-%m-%d")
            
            # הסרת שדות ריקים
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
# בניית המסך (UI)
# ============================================

# כותרת
st.markdown('<div class="main-title">ISO Smart Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">מערכת ניהול משימות 2.0 • Firebase Cloud Edition</div>', unsafe_allow_html=True)

# שעון עצר
days, weeks = get_countdown()
st.markdown(f"""
<div class="countdown-container">
    <div class="countdown-label">🎯 הזמן שנותר לביקורת:</div>
    <div class="countdown-number">{days}</div>
    <div class="countdown-label">ימים (כ-{weeks} שבועות)</div>
</div>
""", unsafe_allow_html=True)

# טעינת נתונים
df = load_tasks()

# מדדים (KPIs)
if not df.empty:
    col1, col2, col3 = st.columns(3)
    
    total = len(df)
    done = len(df[df['סטטוס'].astype(str).str.contains('בוצע')]) if 'סטטוס' in df.columns else 0
    critical = len(df[df['עדיפות'] == 'קריטי']) if 'עדיפות' in df.columns else 0
    
    col1.metric("📋 סה\"כ משימות", total)
    col2.metric("✅ בוצעו בהצלחה", done)
    col3.metric("🚨 קריטי לטיפול", critical)
    
    st.markdown("---")
    
    # גרף פאי
    st.markdown("### 📊 סטטוס משימות")
    if 'סטטוס' in df.columns:
        status_counts = df['סטטוס'].value_counts().reset_index()
        status_counts.columns = ['סטטוס', 'כמות']
        
        # צבעי ניאון לגרף
        fig = px.pie(status_counts, values='כמות', names='סטטוס', 
                     color_discrete_sequence=["#00FFFF", "#FF00FF", "#39FF14", "#FFFF00"],
                     hole=0.4)
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=14),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# טבלה ראשית
st.markdown("### ✏️ רשימת המשימות")
st.caption("ניתן לערוך ישירות בטבלה ולשמור. השינויים נשמרים בענן.")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    key="editor",
    column_config={
        "doc_id": st.column_config.TextColumn(disabled=True),
        "משימה": st.column_config.TextColumn(width="large", required=True),
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

# כפתור שמירה
if st.button("💾 שמור שינויים לענן", type="primary", use_container_width=True):
    if save_task(edited_df):
        st.balloons() # הבלונים חזרו!
        st.success("הנתונים נשמרו בהצלחה ב-Firebase!")
        st.rerun()

# קרדיט
st.markdown('<br><p style="text-align:center; color:#007FFF; opacity:0.7;">ISO Dashboard 2.0 | Powered by Streamlit & Firebase</p>', unsafe_allow_html=True)