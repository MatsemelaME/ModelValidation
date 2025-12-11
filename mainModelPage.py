import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from google import genai

# --- Configuration ---

SHEET_NAME = "Gemini Logs"  # Make sure your actual Google Sheet has this EXACT name

MODEL_MAPPING = {
    "gemini-3-pro-preview": "gemini-3-pro-preview", 
    # Add other models here
}

# --- Google Sheets Connection ---

@st.cache_resource
def get_sheet_connection():
    """
    Authenticates with Google Sheets using Streamlit secrets
    and opens the specific spreadsheet.
    """
    # Define the scope - what we are allowed to do
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        # Load credentials from secrets.toml
        s_account_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            s_account_info, scopes=scopes
        )
        
        # Authorize the client
        client = gspread.authorize(creds)
        
        # Open the sheet
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
        
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        st.info("💡 Hint: Did you share the Google Sheet with the Service Account email address?")
        return None

# Initialize Sheet
sheet = get_sheet_connection()

# --- Helper Functions ---

def save_to_google_sheets(user_id, model_name, prompt, response):
    """Appends a new row to the Google Sheet."""
    if sheet is None:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # The order here must match your Sheet's columns
    row_data = [user_id, timestamp, model_name, prompt, response]
    
    try:
        sheet.append_row(row_data)
        
        # Update session state for immediate display
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
            
        st.session_state["chat_history"].append({
            "user_id": user_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "response": response
        })
        
    except Exception as e:
        st.error(f"Failed to write to Sheet: {e}")

def get_ai_response(model_selection, user_prompt): 
    try:
        api_key = st.secrets["api_keys"]["google"]
    except KeyError:
        return "Error: Gemini API key not found in secrets."

    try:
        if model_selection in MODEL_MAPPING:
            client = genai.Client(api_key=api_key)
            model_id = MODEL_MAPPING[model_selection]

            response = client.models.generate_content(
                model=model_id,
                contents=user_prompt
            )
            return response.text
        else:
            return "Error: Selected model not configured."

    except Exception as e:
        return f"Error calling API: {str(e)}"

# --- Streamlit Interface ---

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

st.title("🤖 Gemini + Google Sheets Logger")
st.markdown("---")

### 1. Configuration

col1, col2 = st.columns([1, 2])

with col1:
    user_id_input = st.text_input(
        "👤 User ID", 
        placeholder="e.g., student_123",
        help="This ID will be saved to the Google Sheet."
    )
    
    selected_label = st.selectbox(
        "Select AI Model",
        options=list(MODEL_MAPPING.keys())
    )

### 2. User Input

user_prompt = st.text_area(
    "💬 Enter your prompt:", 
    height=150,
    placeholder="Ask Gemini anything..."
)

# 3. Generate Button
if st.button("🚀 Generate Response", type="primary"):
    if not user_id_input.strip():
        st.error("⚠️ Please enter a User ID.")
    elif not user_prompt.strip():
        st.warning("⚠️ Please enter a prompt.")
    else:
        with st.spinner(f"Asking {selected_label}..."):
            # 1. Get AI Response
            ai_reply = get_ai_response(selected_label, user_prompt)
            
            # 2. Display
            st.markdown("### ✨ Response")
            st.code(ai_reply, language="markdown")
            
            # 3. Save to Google Sheets
            save_to_google_sheets(user_id_input, selected_label, user_prompt, ai_reply)
            st.success(f"✅ Logged to Google Sheet: {SHEET_NAME}")

st.markdown("---")

### Optional: View History
# Note: Fetching from Sheets can be slow if it's huge, so we usually rely on Session State
# or fetch only the last few rows if needed.

with st.expander("View Current Session History"):
    history = st.session_state["chat_history"]
    
    if not history:
        st.info("No interactions in this session.")
    else:
        for i, entry in enumerate(reversed(history)):
            st.markdown(f"**{len(history) - i}. User:** `{entry['user_id']}` | **Time:** `{entry['timestamp']}`")
            st.markdown(f"**Prompt:** *{entry['prompt'][:80]}...*")
            st.caption("---")
