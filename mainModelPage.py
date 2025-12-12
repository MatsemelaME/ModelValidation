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
        st.error(f"Failed to write to Sheet: {e}")

# --- Gemini Response ---
def get_ai_response(model_selection, chat_history, system_instruction_text):
    try:
        api_key = st.secrets["api_keys"]["google"]
    except KeyError:
        return "Error: Gemini API key not found in secrets."

    try:
        if model_selection in MODEL_MAPPING:
            client = genai.Client(api_key=api_key)
            model_id = MODEL_MAPPING[model_selection]

            api_contents = []
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                api_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_instruction_text 
            )

            response = client.models.generate_content(
                model=model_id,
                contents=api_contents,
                config=config
            )
            return response.text
        else:
            return "Error: Selected model not configured."
    except Exception as e:
        return f"Error calling API: {str(e)}"

def trigger_clarification():
    st.session_state["auto_execute_clarification"] = True

def clear_chat_history():
    st.session_state["messages"] = []
    st.session_state["auto_execute_clarification"] = False

# ------------------------------------------------------------
#                STREAMLIT INTERFACE
# ------------------------------------------------------------
st.set_page_config(page_title="Gemini Chat", layout="wide")

# State init
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "auto_execute_clarification" not in st.session_state:
    st.session_state["auto_execute_clarification"] = False

# Images
img_col1, img_col2, img_col3 = st.columns(3)
with img_col1:
    st.image("https://placehold.co/400x75/orange/white?text=UFS+Logo", use_container_width=True)
with img_col2:
    st.image("https://placehold.co/400x75/blue/white?text=Afrikaans+Department", use_container_width=True)
with img_col3:
    st.image("https://placehold.co/400x75/blue/white?text=ICDF", use_container_width=True)

st.title("Afrikaans Assistant - Demo")
st.markdown("---")

# --- Config Section ---
with st.container():
    col1, col2 = st.columns([1, 2])
    with col1:
        sub_col1, sub_col2 = st.columns([3, 1])
        with sub_col1:
            user_id_input = st.text_input("👤 User ID", placeholder="student_123")
        with sub_col2:
            st.write("")
            st.write("")
            if st.button("Submit"):
                if user_id_input:
                    st.toast(f"✅ ID Set: {user_id_input}")
                else:
                    st.toast("⚠️ Please type an ID")

        selected_label = st.selectbox("Select AI Model", options=list(MODEL_MAPPING.keys()))
        if st.button("🗑️ Clear Chat History", type="primary"):
            clear_chat_history()
            st.rerun()

    with col2:
        default_system_msg = (
            "You are a helpful Afrikaans tutor. "
            "Explain answers in simple English first, then Afrikaans."
        )
        system_instruction_input = st.text_area(
            "🛠️ System Instruction", value=default_system_msg, height=150
        )

# Additional Rules
rules_input = st.text_area("📘 Add Additional Rules", height=150)
if st.button("💾 Save Rules"):
    st.session_state["stored_rules"] = rules_input
    st.success("Rules saved successfully!")

# ------------------------------------------------------------
#           LANGUAGE SELECTION
# ------------------------------------------------------------
language_options = [
    "English", "Afrikaans", "Zulu", "Xhosa", "Sesotho",
    "Tswana", "Xitsonga", "French", "German"
]
selected_language = st.selectbox("🌍 Choose output language", language_options, index=0)
allowed_languages = ["English", "Afrikaans"]

# ------------------------------------------------------------
# Chat Input
# ------------------------------------------------------------
prompt = st.chat_input("Ask Gemini anything...")
clarification_triggered = st.session_state["auto_execute_clarification"]

final_prompt = None
is_clarification = False

if clarification_triggered:
    if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "assistant":
        final_prompt = "I don't understand the previous explanation. Please break it down further."
        is_clarification = True
    st.session_state["auto_execute_clarification"] = False
elif prompt:
    final_prompt = prompt

# ------------------------------------------------------------
# Execute Prompt
# ------------------------------------------------------------
if final_prompt:
    if not user_id_input.strip():
        st.error("⚠️ Please enter a User ID first.")
    else:
        with st.chat_message("user"):
            st.markdown(final_prompt)
        st.session_state["messages"].append({"role": "user", "content": final_prompt})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response_en = get_ai_response(
                    selected_label,
                    st.session_state["messages"],
                    system_instruction_input
                )

            # LANGUAGE FILTER
            if selected_language not in allowed_languages:
                final_output = "⚠️ I can’t assist you with this language. I only translate Afrikaans and English."
            else:
                lang_code = "af" if selected_language == "Afrikaans" else "en"
                final_output = translate_text(response_en, lang_code)

            st.markdown(final_output)

        st.session_state["messages"].append({"role": "assistant", "content": response_en})

        # Save logs
        save_to_google_sheets(
            user_id_input,
            selected_label,
            final_prompt,
            response_en,
            is_clarification
        )

# Clarification button
if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "assistant":
    st.button("🤔 I don't understand this", on_click=trigger_clarification)
