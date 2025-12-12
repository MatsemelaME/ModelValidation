import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from google import genai
from google.genai import types

# --- Configuration ---
SHEET_NAME = "Gemini Logs"
MODEL_MAPPING = {
    "gemini-3-pro-preview": "gemini-3-pro-preview"
}

# --- Dummy Translation Function ---
def translate_text(text, lang):
    """
    Temporary placeholder to avoid errors.
    Replace with actual model or API translation.
    """
    if lang == "af":
        return "AFRIKAANS: " + text
    return text  # English default

# --- Google Sheets Connection ---
@st.cache_resource
def get_sheet_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        if "gcp_service_account" in st.secrets:
            s_account_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(
                s_account_info, scopes=scopes
            )
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet
        else:
            return None

    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

sheet = get_sheet_connection()


# --- Logging to Sheets ---
def save_to_google_sheets(user_id, model_name, prompt, response, is_clarification):
    if sheet is None:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clarification_log = "TRUE" if is_clarification else "FALSE"
    
    row_data = [user_id, timestamp, model_name, prompt, response, clarification_log]
    
    try:
        sheet.append_row(row_data)
    except Exception as e:
        st
