"""
דשבורד חכם לניהול משימות ISO/BRC 2.0
ISO Smart Dashboard 2.0 - Task Management for Audit Preparation
Firestore Edition - Cloud Database Backend
Dark Mode Edition with Neon Color Palette
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from pathlib import Path

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
# פלטת צבעים ניאון / Neon Color Palette
# ============================================

NEON_COLORS = {
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "lime": "#39FF14",
    "yellow": "#FFFF00",
    "blue": "#007FFF"
}

# מיפוי צבעי ניאון לסטטוסים / Neon colors for statuses
STATUS_COLORS = {
    "בוצע": "#39FF14",       # Neon Lime
    "נתקע": "#FF00FF",       # Neon Magenta
    "בטיפול": "#FFFF00",     # Neon Yellow
    "טרם התחיל": "#00FFFF"   # Neon Cyan
}

# מיפוי צבעי ניאון לעדיפות / Neon colors for priority
PRIORITY_COLORS = {
    "קריטי": "#FF00FF",      # Neon Magenta
    "רגיל": "#00FFFF",       # Neon Cyan
    "נמוך": "#007FFF"        # Electric Blue
}

# רשימת צבעי ניאון לתרשימים / Neon color sequence for charts
NEON_COLOR_SEQUENCE = ["#00FFFF", "#FF00FF", "#39FF14", "#FFFF00", "#007FFF"]

# ============================================
# אתחול Firebase / Firebase Initialization
# ============================================

@st.cache_resource
def initialize_firebase():
    """
    מאתחל את Firebase (פעם אחת בלבד).
    Initializes Firebase (once only, cached).
    """
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred)
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
    """
    טוען נתונים מ-Firestore.
    Loads data from Firestore.
    """
    try:
        if db is None:
            st.error("❌ לא מחובר ל-Firebase!")
            return pd.DataFrame(columns=HEADERS + ["doc_id"])
        
        # Query all documents from the tasks collection
        docs = db.collection(COLLECTION_NAME).stream()
        
        # Convert to list of dictionaries with doc_id
        records = []
        for doc in docs:
            record = doc.to_dict()
            # Add the document ID for update/delete operations
            record["doc_id"] = doc.id
            # Remove metadata fields
            record.pop("_uploaded_at", None)
            record.pop("_source_row", None)
            records.append(record)
        
        if not records:
            st.info("📝 אין משימות ב-Firestore. הוסף משימות חדשות בטבלה למטה.")
            return pd.DataFrame(columns=HEADERS + ["doc_id"])
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Handle date column - convert string to date object
        if "תאריך יעד" in df.columns:
            def parse_date(val):
                if val is None or pd.isna(val):
                    return None
                try:
                    if isinstance(val, str):
                        # Try different date formats
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                            try:
                                return datetime.strptime(val, fmt).date()
                            except:
                                continue
                    return None
                except:
                    return None
            
            df["תאריך יעד"] = df["תאריך יעד"].apply(parse_date)
        
        # Ensure doc_id is the last column
        if "doc_id" in df.columns:
            cols = [c for c in df.columns if c != "doc_id"] + ["doc_id"]
            df = df[cols]
        
        return df
    
    except Exception as e:
        st.error(f"❌ שגיאה בטעינת נתונים מ-Firestore: {str(e)}")
        return pd.DataFrame(columns=HEADERS + ["doc_id"])


def save_data(df: pd.DataFrame) -> bool:
    """
    שומר את הנתונים ל-Firestore.
    Saves data to Firestore.
    Updates existing documents or creates new ones.
    """
    try:
        if db is None:
            st.error("❌ לא מחובר ל-Firebase!")
            return False
        
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # Convert row to dictionary
                row_data = row.to_dict()
                
                # Extract doc_id (if exists)
                doc_id = row_data.pop("doc_id", None)
                
                # Convert date to string for Firestore
                if "תאריך יעד" in row_data and row_data["תאריך יעד"] is not None:
                    if isinstance(row_data["תאריך יעד"], (date, datetime)):
                        row_data["תאריך יעד"] = row_data["תאריך יעד"].strftime("%Y-%m-%d")
                
                # Clean None values and convert numpy types
                cleaned_data = {}
                for key, value in row_data.items():
                    if pd.isna(value):
                        cleaned_data[key] = None
                    elif hasattr(value, 'item'):  # numpy type
                        cleaned_data[key] = value.item()
                    else:
                        cleaned_data[key] = value
                
                # Add timestamp
                cleaned_data["_updated_at"] = firestore.SERVER_TIMESTAMP
                
                if doc_id and doc_id != "" and not pd.isna(doc_id):
                    # Update existing document
                    db.collection(COLLECTION_NAME).document(doc_id).set(cleaned_data)
                else:
                    # Create new document
                    db.collection(COLLECTION_NAME).add(cleaned_data)
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                st.error(f"❌ שגיאה בשמירת שורה {index}: {str(e)}")
        
        return success_count > 0
    
    except Exception as e:
        st.error(f"❌ שגיאה בשמירת נתונים ל-Firestore: {str(e)}")
        return False


def delete_document(doc_id: str) -> bool:
    """
    מוחק מסמך מ-Firestore.
    Deletes a document from Firestore.
    """
    try:
        if db is None:
            return False
        db.collection(COLLECTION_NAME).document(doc_id).delete()
        return True
    except Exception as e:
        st.error(f"❌ שגיאה במחיקת מסמך: {str(e)}")
        return False


def get_countdown() -> dict:
    """
    מחשב את הימים שנותרו עד מועד הביקורת.
    Calculates remaining days until the audit date.
    """
    now = datetime.now()
    delta = TARGET_DATE - now
    remaining_days = delta.days
    
    # חישוב שבועות וחודשים / Calculate weeks and months
    weeks = remaining_days // 7
    months = remaining_days // 30
    
    return {
        "days": remaining_days,
        "weeks": weeks,
        "months": months,
        "is_past": remaining_days < 0
    }


def get_motivation_message(days_remaining: int) -> str:
    """
    מחזיר הודעה מוטיבציונית בהתאם לזמן שנותר.
    Returns motivational message based on remaining time.
    """
    if days_remaining < 0:
        return "⚠️ מועד הביקורת עבר! יש לעדכן את לוח הזמנים."
    elif days_remaining <= 30:
        return "🔥 פחות מחודש! זה הזמן לסיים את כל המשימות הפתוחות!"
    elif days_remaining <= 90:
        return "⏰ פחות מ-3 חודשים - מומלץ להתחיל להאיץ!"
    elif days_remaining <= 180:
        return "💪 עוד כחצי שנה - נמשיך בקצב טוב!"
    else:
        return "✨ יש זמן להתכונן כראוי - שמרו על הקצב!"


def sort_by_priority(df: pd.DataFrame) -> pd.DataFrame:
    """
    ממיין את הטבלה לפי עדיפות - קריטי למעלה.
    Sorts the table by priority - critical first.
    """
    if "עדיפות" not in df.columns or df.empty:
        return df
    
    priority_order = {"קריטי": 0, "רגיל": 1, "נמוך": 2}
    df["_priority_sort"] = df["עדיפות"].map(priority_order).fillna(3)
    df = df.sort_values("_priority_sort").drop("_priority_sort", axis=1)
    return df.reset_index(drop=True)


# ============================================
# הגדרת הדף / Page Configuration
# ============================================

st.set_page_config(
    page_title="ISO Smart Dashboard 2.0",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# עיצוב CSS מותאם - מצב כהה / Dark Mode Custom CSS
# ============================================

st.markdown("""
<style>
    /* ============================================ */
    /* Dark Mode Base Styles */
    /* ============================================ */
    
    /* Force dark background */
    .stApp {
        background-color: #0E1117 !important;
    }
    
    .main {
        direction: rtl;
        text-align: right;
        background-color: #0E1117 !important;
    }
    
    /* All text to light color */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div {
        color: #FAFAFA !important;
    }
    
    /* ============================================ */
    /* Headers with Neon Glow */
    /* ============================================ */
    
    .main-title {
        text-align: center;
        color: #00FFFF !important;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 10px #00FFFF, 0 0 20px #00FFFF, 0 0 30px #00FFFF;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .sub-title {
        text-align: center;
        color: #FF00FF !important;
        font-size: 1.3rem;
        margin-bottom: 2rem;
        text-shadow: 0 0 5px #FF00FF;
    }
    
    .cloud-badge {
        text-align: center;
        color: #39FF14 !important;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    
    /* ============================================ */
    /* Countdown Container - Neon Gradient */
    /* ============================================ */
    
    .countdown-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 2px solid #00FFFF;
        border-radius: 20px;
        padding: 2.5rem;
        text-align: center;
        color: #FAFAFA;
        margin-bottom: 2rem;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.3), 
                    0 0 40px rgba(0, 255, 255, 0.1),
                    inset 0 0 20px rgba(0, 255, 255, 0.05);
    }
    
    .countdown-number {
        font-size: 5rem;
        font-weight: bold;
        margin: 0;
        color: #00FFFF !important;
        text-shadow: 0 0 20px #00FFFF, 0 0 40px #00FFFF;
    }
    
    .countdown-label {
        font-size: 1.3rem;
        opacity: 0.95;
        color: #FAFAFA !important;
    }
    
    /* ============================================ */
    /* Motivation Text - Neon Border */
    /* ============================================ */
    
    .motivation-text {
        background-color: rgba(26, 26, 46, 0.8);
        border-right: 4px solid #FF00FF;
        border-left: 1px solid #FF00FF;
        padding: 1.2rem;
        border-radius: 0 12px 12px 0;
        margin: 1.5rem 0;
        font-size: 1.2rem;
        color: #FAFAFA !important;
        box-shadow: 0 0 15px rgba(255, 0, 255, 0.2);
    }
    
    /* ============================================ */
    /* KPI Cards */
    /* ============================================ */
    
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #00FFFF;
        border-radius: 15px;
        padding: 1rem;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
    }
    
    [data-testid="stMetricLabel"] {
        color: #00FFFF !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #FAFAFA !important;
        font-size: 2rem !important;
    }
    
    [data-testid="stMetricDelta"] {
        color: #39FF14 !important;
    }
    
    /* ============================================ */
    /* Section Headers */
    /* ============================================ */
    
    h3, .stMarkdown h3 {
        color: #00FFFF !important;
        text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
        border-bottom: 1px solid rgba(0, 255, 255, 0.3);
        padding-bottom: 0.5rem;
    }
    
    h4, .stMarkdown h4 {
        color: #FF00FF !important;
        text-shadow: 0 0 5px rgba(255, 0, 255, 0.5);
    }
    
    /* ============================================ */
    /* Data Editor / Table Styling */
    /* ============================================ */
    
    .stDataEditor {
        direction: rtl;
    }
    
    [data-testid="stDataFrame"], 
    [data-testid="stDataEditor"] {
        background-color: #1a1a2e !important;
        border: 1px solid #007FFF;
        border-radius: 10px;
    }
    
    /* ============================================ */
    /* Buttons - Neon Style */
    /* ============================================ */
    
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #00FFFF;
        color: #00FFFF !important;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #00FFFF 0%, #007FFF 100%);
        color: #0E1117 !important;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
    }
    
    /* ============================================ */
    /* Multiselect / Selectbox */
    /* ============================================ */
    
    .stMultiSelect, .stSelectbox {
        background-color: #1a1a2e;
    }
    
    [data-baseweb="select"] {
        background-color: #1a1a2e !important;
        border-color: #007FFF !important;
    }
    
    /* ============================================ */
    /* Progress Bar - Neon */
    /* ============================================ */
    
    .stProgress > div > div {
        background-color: #39FF14 !important;
        box-shadow: 0 0 10px #39FF14;
    }
    
    /* ============================================ */
    /* Dividers */
    /* ============================================ */
    
    hr {
        border-color: rgba(0, 255, 255, 0.3) !important;
    }
    
    /* ============================================ */
    /* Checkbox */
    /* ============================================ */
    
    .stCheckbox label span {
        color: #FAFAFA !important;
    }
    
    /* ============================================ */
    /* Footer */
    /* ============================================ */
    
    .footer-text {
        text-align: center;
        color: #007FFF !important;
        padding: 1.5rem;
        font-size: 0.9rem;
    }
    
    .footer-text a {
        color: #00FFFF !important;
    }
    
    /* ============================================ */
    /* Scrollbar - Dark Theme */
    /* ============================================ */
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0E1117;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #007FFF;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00FFFF;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# כותרת ראשית / Main Header
# ============================================

st.markdown('<h1 class="main-title">📋 ISO Smart Dashboard 2.0</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">מערכת ניהול משימות להכנה לביקורת ISO/BRC</p>', unsafe_allow_html=True)
st.markdown('<p class="cloud-badge">☁️ מחובר ל-Firebase Cloud</p>', unsafe_allow_html=True)

# ============================================
# ספירה לאחור / Countdown Section
# ============================================

countdown = get_countdown()

st.markdown(f"""
<div class="countdown-container">
    <p class="countdown-label">🎯 ביקורת ISO/BRC מתוכננת ל-1 ביוני 2026</p>
    <p class="countdown-number">{abs(countdown['days'])} {'ימים' if countdown['days'] >= 0 else 'ימים שעברו'}</p>
    <p class="countdown-label">📅 כ-{countdown['weeks']} שבועות | כ-{countdown['months']} חודשים</p>
</div>
""", unsafe_allow_html=True)

# הודעה מוטיבציונית / Motivational Message
motivation = get_motivation_message(countdown['days'])
st.markdown(f'<div class="motivation-text">{motivation}</div>', unsafe_allow_html=True)

st.divider()

# ============================================
# טעינת נתונים / Load Data
# ============================================

df = load_data()

# ============================================
# סטטיסטיקות / Statistics Section (Status Overview)
# ============================================

st.markdown("### 📊 סקירת סטטוס")

if not df.empty and "סטטוס" in df.columns:
    total_tasks = len(df)
    critical_tasks = len(df[df["עדיפות"] == "קריטי"]) if "עדיפות" in df.columns else 0
    in_progress_tasks = len(df[df["סטטוס"].str.contains("בטיפול", na=False)])
    done_tasks = len(df[df["סטטוס"].str.contains("בוצע", na=False)])
    stuck_tasks = len(df[df["סטטוס"].str.contains("נתקע", na=False)])
    not_started = len(df[df["סטטוס"].str.contains("טרם התחיל", na=False)])
    
    # ============================================
    # שורת KPI - 3 מדדים עיקריים / KPI Row - 3 Main Metrics
    # ============================================
    
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    
    with kpi_col1:
        st.metric(
            label="📋 סה\"כ משימות",
            value=total_tasks,
            delta=None
        )
    
    with kpi_col2:
        st.metric(
            label="✅ משימות שבוצעו",
            value=done_tasks,
            delta=f"{(done_tasks/total_tasks*100):.1f}%" if total_tasks > 0 else "0%"
        )
    
    with kpi_col3:
        st.metric(
            label="🚨 לטיפול מיידי",
            value=critical_tasks,
            delta="קריטי" if critical_tasks > 0 else None,
            delta_color="inverse"
        )
    
    # ============================================
    # תרשים עוגה - התפלגות סטטוס / Pie Chart - Status Distribution
    # ============================================
    
    st.markdown("#### 🥧 התפלגות סטטוס משימות")
    
    # הכנת נתונים לתרשים / Prepare data for chart
    # Clean status values for chart (remove emoji prefixes)
    df_chart = df.copy()
    df_chart["סטטוס_נקי"] = df_chart["סטטוס"].str.replace(r"^[^\w]+", "", regex=True).str.strip()
    status_counts = df_chart["סטטוס_נקי"].value_counts().reset_index()
    status_counts.columns = ["סטטוס", "כמות"]
    
    # צבעי ניאון לסטטוסים / Neon colors for statuses
    neon_color_map = {
        "בוצע": "#39FF14",       # Neon Lime
        "נתקע": "#FF00FF",       # Neon Magenta
        "בטיפול": "#FFFF00",     # Neon Yellow
        "טרם התחיל": "#00FFFF"   # Neon Cyan
    }
    
    fig = px.pie(
        status_counts,
        values="כמות",
        names="סטטוס",
        title="",
        color="סטטוס",
        color_discrete_map=neon_color_map,
        hole=0.45  # Donut style
    )
    
    # עיצוב תרשים כהה / Dark theme chart styling
    fig.update_layout(
        font=dict(size=14, color="#FAFAFA", family="Segoe UI"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(color="#FAFAFA", size=12)
        ),
        margin=dict(t=30, b=30, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",   # Transparent plot area
        showlegend=True
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        textfont=dict(size=13, color="#0E1117", family="Segoe UI"),
        marker=dict(
            line=dict(color='#0E1117', width=2)  # Dark border between slices
        ),
        hovertemplate="<b>%{label}</b><br>כמות: %{value}<br>אחוז: %{percent}<extra></extra>"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # פס התקדמות / Progress Bar
    if total_tasks > 0:
        progress = done_tasks / total_tasks
        st.progress(progress, text=f"התקדמות כללית: {progress*100:.1f}% ({done_tasks} מתוך {total_tasks} משימות הושלמו)")

else:
    st.info("📝 אין משימות עדיין או שהקובץ לא נטען כראוי.")

st.divider()

# ============================================
# סינון וחיפוש / Filtering & Search
# ============================================

st.markdown("### 🔍 סינון משימות")

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    # סינון לפי סטטוס / Filter by Status
    status_filter = st.multiselect(
        "סטטוס",
        options=STATUS_OPTIONS,
        default=None,
        placeholder="בחר סטטוס..."
    )

with filter_col2:
    # סינון לפי עדיפות / Filter by Priority
    priority_filter = st.multiselect(
        "עדיפות",
        options=PRIORITY_OPTIONS,
        default=None,
        placeholder="בחר עדיפות..."
    )

with filter_col3:
    # סינון לפי תקן / Filter by Standard
    if "תקן" in df.columns:
        standards = df["תקן"].dropna().unique().tolist()
        standard_filter = st.multiselect(
            "תקן",
            options=standards,
            default=None,
            placeholder="בחר תקן..."
        )
    else:
        standard_filter = []

with filter_col4:
    # סינון לפי מחלקה / Filter by Department
    if "מחלקה" in df.columns:
        departments = df["מחלקה"].dropna().unique().tolist()
        dept_filter = st.multiselect(
            "מחלקה",
            options=departments,
            default=None,
            placeholder="בחר מחלקה..."
        )
    else:
        dept_filter = []

# יישום הסינון / Apply Filters
filtered_df = df.copy()

if status_filter:
    # Handle status filter with partial matching (for emoji prefixes)
    mask = filtered_df["סטטוס"].apply(lambda x: any(s in str(x) for s in status_filter))
    filtered_df = filtered_df[mask]

if priority_filter:
    filtered_df = filtered_df[filtered_df["עדיפות"].isin(priority_filter)]

if standard_filter:
    filtered_df = filtered_df[filtered_df["תקן"].isin(standard_filter)]

if dept_filter:
    filtered_df = filtered_df[filtered_df["מחלקה"].isin(dept_filter)]

# מיון לפי עדיפות / Sort by priority
show_critical_first = st.checkbox("🔺 הצג משימות קריטיות בראש הרשימה", value=True)
if show_critical_first:
    filtered_df = sort_by_priority(filtered_df)

st.divider()

# ============================================
# עורך משימות / Task Editor
# ============================================

st.markdown("### ✏️ ניהול משימות")
st.caption(f"💡 מוצגות {len(filtered_df)} משימות מתוך {len(df)} | עריכה ישירה בטבלה. לחץ 'שמור שינויים' לעדכון ב-Cloud.")

# הגדרת עמודות / Column Configuration
column_config = {
    "doc_id": st.column_config.TextColumn(
        "doc_id",
        help="מזהה מסמך Firestore - אל תערוך!",
        disabled=True,
        width="small"
    ),
    "מס\"ד": st.column_config.NumberColumn(
        "מס\"ד",
        help="מספר סידורי",
        width="small"
    ),
    "תקן": st.column_config.TextColumn(
        "תקן",
        help="שם התקן (ISO, BRC, וכו')",
        width="small"
    ),
    "קטגוריה": st.column_config.TextColumn(
        "קטגוריה",
        help="קטגוריה ראשית",
        width="medium"
    ),
    "תת-קטגוריה": st.column_config.TextColumn(
        "תת-קטגוריה",
        help="תת-קטגוריה",
        width="medium"
    ),
    "סעיף": st.column_config.TextColumn(
        "סעיף",
        help="מספר הסעיף בתקן",
        width="small"
    ),
    "משימה": st.column_config.TextColumn(
        "משימה",
        help="תיאור המשימה",
        width="large",
        required=True
    ),
    "תיאור מפורט": st.column_config.TextColumn(
        "תיאור מפורט",
        help="פירוט נוסף על המשימה",
        width="large"
    ),
    "מחלקה": st.column_config.TextColumn(
        "מחלקה",
        help="המחלקה האחראית",
        width="medium"
    ),
    "תאריך יעד": st.column_config.DateColumn(
        "תאריך יעד",
        help="תאריך היעד להשלמת המשימה",
        format="DD/MM/YYYY",
        width="small"
    ),
    "עדיפות": st.column_config.SelectboxColumn(
        "עדיפות",
        help="רמת העדיפות של המשימה",
        options=PRIORITY_OPTIONS,
        width="small",
        required=True
    ),
    "סטטוס": st.column_config.SelectboxColumn(
        "סטטוס",
        help="סטטוס המשימה",
        options=STATUS_OPTIONS,
        width="small",
        required=True
    ),
    "הערות": st.column_config.TextColumn(
        "הערות",
        help="הערות נוספות",
        width="medium"
    ),
    "משך משוער": st.column_config.TextColumn(
        "משך משוער",
        help="זמן משוער לביצוע",
        width="small"
    )
}

# Columns to display (hide doc_id from main view but keep in data)
display_columns = [c for c in filtered_df.columns if c != "doc_id"]

# עורך הנתונים / Data Editor
edited_df = st.data_editor(
    filtered_df,
    column_config=column_config,
    column_order=display_columns + ["doc_id"],  # doc_id at the end
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="task_editor"
)

# כפתור שמירה / Save Button
col_save, col_refresh = st.columns(2)

with col_save:
    if st.button("💾 שמור שינויים ל-Cloud", use_container_width=True, type="primary"):
        with st.spinner("שומר ל-Firestore..."):
            if save_data(edited_df):
                st.success("✅ השינויים נשמרו בהצלחה ל-Firebase!")
                st.rerun()

with col_refresh:
    if st.button("🔄 רענן מ-Cloud", use_container_width=True):
        st.rerun()

st.divider()

# ============================================
# פעולות נוספות / Additional Actions
# ============================================

st.markdown("### 🛠️ פעולות מהירות")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📥 הורד לאקסל", use_container_width=True):
        # יצוא לאקסל / Export to Excel
        try:
            # Remove doc_id from export
            export_df = edited_df.drop(columns=["doc_id"], errors="ignore")
            output_file = "ISO_tasks_export.xlsx"
            export_df.to_excel(output_file, index=False, engine='openpyxl')
            with open(output_file, "rb") as f:
                st.download_button(
                    label="📥 לחץ להורדה",
                    data=f,
                    file_name=f"משימות_ISO_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"שגיאה בייצוא: {str(e)}")

with col2:
    if st.button("🗑️ נקה משימות שבוצעו", use_container_width=True):
        if not df.empty and "סטטוס" in df.columns:
            done_docs = df[df["סטטוס"].str.contains("בוצע", na=False)]
            if len(done_docs) > 0:
                with st.spinner("מוחק משימות שבוצעו..."):
                    deleted = 0
                    for _, row in done_docs.iterrows():
                        if "doc_id" in row and delete_document(row["doc_id"]):
                            deleted += 1
                    if deleted > 0:
                        st.success(f"✅ נמחקו {deleted} משימות שבוצעו!")
                        st.rerun()
            else:
                st.info("אין משימות שבוצעו למחיקה.")

with col3:
    if st.button("⬆️ סדר לפי עדיפות", use_container_width=True):
        sorted_df = sort_by_priority(df)
        st.info("💡 המיון מוצג בטבלה למעלה (לא משנה את הסדר ב-Cloud)")

# ============================================
# סיכום לפי תקנים / Summary by Standard
# ============================================

if not df.empty and "תקן" in df.columns:
    st.divider()
    st.markdown("### 📈 סיכום לפי תקן")
    
    summary_cols = st.columns(2)
    
    with summary_cols[0]:
        # סיכום לפי תקן / Summary by Standard
        standard_summary = df.groupby("תקן").agg({
            "משימה": "count",
            "סטטוס": lambda x: x.str.contains("בוצע", na=False).sum()
        }).rename(columns={"משימה": "סה״כ", "סטטוס": "הושלמו"})
        standard_summary["אחוז השלמה"] = (standard_summary["הושלמו"] / standard_summary["סה״כ"] * 100).round(1).astype(str) + "%"
        st.dataframe(standard_summary, use_container_width=True)
    
    with summary_cols[1]:
        # סיכום לפי מחלקה / Summary by Department
        if "מחלקה" in df.columns:
            dept_summary = df.groupby("מחלקה").agg({
                "משימה": "count",
                "סטטוס": lambda x: x.str.contains("בוצע", na=False).sum()
            }).rename(columns={"משימה": "סה״כ", "סטטוס": "הושלמו"})
            dept_summary["אחוז השלמה"] = (dept_summary["הושלמו"] / dept_summary["סה״כ"] * 100).round(1).astype(str) + "%"
            st.dataframe(dept_summary, use_container_width=True)

# ============================================
# סרגל תחתון / Footer
# ============================================

st.divider()
st.markdown(f"""
<div class="footer-text">
    <p>🌟 ISO Smart Dashboard 2.0 | ☁️ Firebase Cloud Edition | נבנה עם ❤️ ב-Streamlit</p>
    <p style="font-size: 0.8rem; color: #007FFF;">Collection: {COLLECTION_NAME} | עדכון אחרון: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
</div>
""", unsafe_allow_html=True)
