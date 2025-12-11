import streamlit as st
import json
import os
from datetime import datetime
from google import genai

# --- Firebase Imports ---
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# --- Configuration & Setup ---

# REVERTED: Kept your original model mapping
MODEL_MAPPING = {
    "gemini-3-pro-preview": "gemini-3-pro-preview", 
    # Updated to a currently active model ID for testing
}

# --- Database Connection ---

@st.cache_resource
def get_db():
    """
    Initializes Firebase only once. 
    Using cache_resource ensures we don't reconnect on every rerun.
    """
    try:
        # Check if app is already initialized to avoid "App already exists" error
        if not firebase_admin._apps:
            # Create a credential object from the secrets dictionary
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to initialize Firebase: {e}")
        return None

# Initialize DB
db = get_db()

# --- Helper Functions ---

# UPDATED: Added user_id parameter
def save_interaction_to_firebase(user_id, model_name, prompt, response):
    """Saves the interaction to Firestore with the User ID."""
    
    if db is None:
        st.error("Database connection not active.")
        return

    entry = {
        "user_id": user_id,          # <--- Captured User ID
        "timestamp": datetime.now(), # Firestore handles datetime objects natively
        "model": model_name,
        "prompt": prompt,
        "response": response
    }
    
    try:
        # 'history' is the name of your collection in Firestore
        db.collection("history").add(entry)
        
        # We also keep it in session state for immediate display without re-fetching
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        
        # Convert datetime to string for session state display
        display_entry = entry.copy()
        display_entry["timestamp"] = entry["timestamp"].isoformat()
        st.session_state["chat_history"].append(display_entry)
        
    except Exception as e:
        st.error(f"Failed to save to Firebase: {e}")

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

st.title("🤖 Gemini + Firebase Logger")
st.markdown("---")

### 1. Configuration (User ID & Model)

col1, col2 = st.columns([1, 2])

with col1:
    # UPDATED: Added User ID Input Field
    user_id_input = st.text_input(
        "👤 User ID", 
        placeholder="e.g., student_123",
        help="This ID will be saved with your prompt logs."
    )
    
    selected_label = st.selectbox(
        "Select AI Model",
        options=list(MODEL_MAPPING.keys())
    )

### 2. User Input Area

user_prompt = st.text_area(
    "💬 Enter your prompt:", 
    height=150,
    placeholder="Ask Gemini anything..."
)

# 3. Generate Button
if st.button("🚀 Generate Response", type="primary"):
    # UPDATED: Validation checks
    if not user_id_input.strip():
        st.error("⚠️ Please enter a User ID before generating.")
    elif not user_prompt.strip():
        st.warning("⚠️ Please enter a prompt.")
    else:
        with st.spinner(f"Asking {selected_label}..."):
            ai_reply = get_ai_response(selected_label, user_prompt)
            
            st.markdown("### ✨ Response")
            st.code(ai_reply, language="markdown")
            
            # UPDATED: Save to Firebase with user_id_input
            save_interaction_to_firebase(user_id_input, selected_label, user_prompt, ai_reply)
            st.success(f"Saved to Firestore for user: {user_id_input}!")

st.markdown("---")

### Optional: View History

with st.expander("View Current Session History"):
    history = st.session_state["chat_history"]
    
    if not history:
        st.info("No interactions in this session.")
    else:
        for i, entry in enumerate(reversed(history)):
            # Displaying User ID in history
            st.markdown(f"**{len(history) - i}. User:** `{entry.get('user_id', 'Unknown')}` | **Time:** `{entry['timestamp']}`")
            st.markdown(f"**Prompt:** *{entry['prompt'][:80]}...*")
            st.caption("---")
