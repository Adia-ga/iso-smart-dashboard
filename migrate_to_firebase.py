"""
Firebase Migration Script (Debug Mode)
מעלה נתונים מקובץ האקסל המקומי ל-Firestore
Uploads data from local Excel file to Firestore
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

# Firebase imports
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# Configuration / הגדרות
# ============================================

EXCEL_FILE = "ISO BRC TASKS. updated.xlsx"
SERVICE_ACCOUNT_KEY = "serviceAccountKey.json"
COLLECTION_NAME = "tasks"

# Debug mode - set to True to see detailed output
DEBUG_MODE = True

# ============================================
# Initialize Firebase / אתחול Firebase
# ============================================

def initialize_firebase():
    """
    מאתחל את אפליקציית Firebase.
    Initializes the Firebase application.
    Returns the Firestore client.
    """
    try:
        # Check if app is already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully!")
        else:
            print("ℹ️ Firebase app already initialized.")
        
        # Get Firestore client
        db = firestore.client()
        return db
    
    except FileNotFoundError:
        print(f"❌ Error: Service account key file '{SERVICE_ACCOUNT_KEY}' not found!")
        print("   Please download your Firebase service account key and place it in the project folder.")
        return None
    
    except Exception as e:
        print(f"❌ Error initializing Firebase: {str(e)}")
        return None


# ============================================
# Load and Clean Data / טעינה וניקוי נתונים
# ============================================

def clean_value(val):
    """
    ניקוי ערך בודד - המרה לסוגי Python מקוריים.
    Clean a single value - convert to native Python types.
    """
    # Handle None and NaN
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    
    # Handle numpy types
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        if np.isnan(val):
            return None
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)
    
    # Handle pandas Timestamp
    if isinstance(val, pd.Timestamp):
        if pd.isna(val):
            return None
        return val.strftime("%Y-%m-%d")
    
    # Handle datetime
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    
    # Handle strings
    if isinstance(val, str):
        return val.strip() if val.strip() else None
    
    return val


def load_and_clean_data():
    """
    טוען את קובץ האקסל ומנקה את הנתונים להעלאה ל-Firestore.
    Loads the Excel file and cleans data for Firestore upload.
    """
    try:
        print(f"\n📂 Loading Excel file: {EXCEL_FILE}")
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        print(f"   Found {len(df)} rows and {len(df.columns)} columns.")
        print(f"   Columns: {list(df.columns)}")
        
        # ============================================
        # Data Cleaning / ניקוי נתונים
        # ============================================
        
        print("\n🧹 Cleaning data...")
        
        # 1. Convert all values using the clean_value function
        for col in df.columns:
            df[col] = df[col].apply(clean_value)
            
            # Debug: show sample of cleaned column
            if DEBUG_MODE:
                non_null = df[col].dropna()
                sample = non_null.iloc[0] if len(non_null) > 0 else None
                sample_type = type(sample).__name__ if sample is not None else "None"
                print(f"   📋 Column '{col}': type={sample_type}, sample={repr(sample)[:50]}")
        
        print("\n✅ Data cleaning complete!")
        return df
    
    except FileNotFoundError:
        print(f"❌ Error: Excel file '{EXCEL_FILE}' not found!")
        return None
    
    except Exception as e:
        print(f"❌ Error loading Excel file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# Upload to Firestore / העלאה ל-Firestore
# ============================================

def upload_to_firestore(db, df):
    """
    מעלה את הנתונים ל-Firestore.
    Uploads data to Firestore.
    """
    if db is None or df is None:
        print("❌ Cannot upload: Database or data is missing.")
        return False
    
    print(f"\n🚀 Starting upload to Firestore collection: '{COLLECTION_NAME}'")
    print(f"   Total documents to upload: {len(df)}")
    print("-" * 60)
    
    # Convert DataFrame to list of dictionaries
    records = df.to_dict(orient='records')
    
    # ============================================
    # DEBUG: Inspect first record before upload
    # ============================================
    if DEBUG_MODE and len(records) > 0:
        print("\n🔍 DEBUG: First record inspection:")
        print("-" * 40)
        first_record = records[0]
        for key, value in first_record.items():
            val_type = type(value).__name__
            print(f"   {key}: ({val_type}) {repr(value)[:60]}")
        print("-" * 40)
        
        # Check for any problematic values
        print("\n🔍 DEBUG: Checking for problematic values in first record...")
        for key, value in first_record.items():
            if isinstance(value, float) and np.isnan(value):
                print(f"   ⚠️ WARNING: NaN found in '{key}'!")
            if isinstance(value, (np.integer, np.floating, np.bool_)):
                print(f"   ⚠️ WARNING: NumPy type found in '{key}': {type(value)}")
        print("-" * 40)
    
    success_count = 0
    error_count = 0
    
    for index, record in enumerate(records):
        try:
            # Add metadata for tracking
            record['_uploaded_at'] = firestore.SERVER_TIMESTAMP
            record['_source_row'] = index + 2  # +2 for header row and 0-indexing
            
            # ============================================
            # UPLOAD - with detailed error catching
            # ============================================
            doc_ref = db.collection(COLLECTION_NAME).add(record)
            
            success_count += 1
            
            # Progress log every 10 documents
            if (index + 1) % 10 == 0 or (index + 1) == len(records):
                print(f"   📤 Uploaded {index + 1}/{len(records)} documents...")
        
        except Exception as e:
            error_count += 1
            
            # ============================================
            # DEBUG: Detailed error output
            # ============================================
            print(f"\n❌ ERROR on row {index + 2}:")
            print(f"   Exception Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)[:500]}")
            
            if DEBUG_MODE:
                print(f"\n   🔍 Problematic record data:")
                for key, value in record.items():
                    if key.startswith('_'):
                        continue
                    val_type = type(value).__name__
                    print(f"      {key}: ({val_type}) {repr(value)[:40]}")
                
                # Print full traceback
                import traceback
                print(f"\n   📋 Full traceback:")
                traceback.print_exc()
            
            # ============================================
            # BREAK after first error (as requested)
            # ============================================
            print(f"\n   ⛔ Stopping after first error for debugging.")
            print(f"   💡 Fix the issue and re-run the script.")
            break
    
    print("\n" + "-" * 60)
    print(f"\n📊 Upload Summary:")
    print(f"   ✅ Successfully uploaded: {success_count} documents")
    if error_count > 0:
        print(f"   ❌ Failed: {error_count} documents (stopped at first error)")
    print(f"   📁 Collection: {COLLECTION_NAME}")
    
    return success_count > 0


# ============================================
# Main Execution / הרצה ראשית
# ============================================

def main():
    """
    פונקציה ראשית - מריצה את כל תהליך ההעברה.
    Main function - runs the entire migration process.
    """
    print("=" * 60)
    print("🔥 Firebase Migration Script (DEBUG MODE)")
    print("   Excel → Firestore")
    print("=" * 60)
    
    # Step 1: Initialize Firebase
    print("\n[Step 1/3] Initializing Firebase...")
    db = initialize_firebase()
    if db is None:
        print("\n❌ Migration aborted: Firebase initialization failed.")
        return
    
    # Step 2: Load and clean data
    print("\n[Step 2/3] Loading and cleaning data...")
    df = load_and_clean_data()
    if df is None:
        print("\n❌ Migration aborted: Data loading failed.")
        return
    
    # Step 3: Upload to Firestore
    print("\n[Step 3/3] Uploading to Firestore...")
    success = upload_to_firestore(db, df)
    
    # Final message
    print("\n" + "=" * 60)
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("⚠️ Migration completed with errors.")
        print("\n💡 Common fixes:")
        print("   1. Enable Firestore API in Google Cloud Console")
        print("   2. Check service account permissions")
        print("   3. Verify Firestore database exists in your project")
    print("=" * 60)


if __name__ == "__main__":
    main()
