import streamlit as st
import json
import os
from datetime import datetime
from google import genai

# --- Configuration & Setup ---
JSON_DB_FILE = "history.json"

# Mapping user-friendly names to actual API model IDs
MODEL_MAPPING = {        
    # Using gemini-1.5-pro as the working standard. 
    # Change "gemini-1.5-pro" to "gemini-3-pro-preview" if/when available.
    "Gemini3 pro": "gemini-3-pro-preview", 
}

# --- Helper Functions ---

def load_history():
    """Loads the history from the JSON file. Returns an empty list if file doesn't exist."""
    if not os.path.exists(JSON_DB_FILE):
        return []
    try:
        with open(JSON_DB_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_interaction(model_name, prompt, response):
    """Appends a new interaction to the JSON file."""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "prompt": prompt,
        "response": response
    }
    
    history.append(entry)
    
    with open(JSON_DB_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_ai_response(model_selection, user_prompt):
    """Routes the prompt to the correct API based on selection."""
    
    # We assume secrets.toml still has [api_keys] -> google = "..."
    api_keys = st.secrets["api_keys"]
    
    try:
        if model_selection == "Gemini3 pro":
            client = genai.Client(api_key=api_keys["google"])
            response = client.models.generate_content(
                model=MODEL_MAPPING[model_selection],
                contents=user_prompt
            )
            return response.text
        else:
            return "Error: Selected model not configured in backend."

    except Exception as e:
        return f"Error calling API: {str(e)}"

# --- Streamlit Interface ---

st.title("Gemini Interface")

# 1. Model Selection
# kept as a selectbox so you can easily add the others back later
selected_label = st.selectbox(
    "Select AI Model",
    options=list(MODEL_MAPPING.keys())
)

# 2. User Input
user_prompt = st.text_area("Enter your prompt:", height=150)

# 3. Generate Button
if st.button("Generate Response"):
    if not user_prompt.strip():
        st.warning("Please enter a prompt first.")
    else:
        with st.spinner(f"Asking {selected_label}..."):
            # Get response from the actual API
            ai_reply = get_ai_response(selected_label, user_prompt)
            
            # Display response
            st.markdown("### Response")
            st.write(ai_reply)
            
            # Save to JSON DB
            save_interaction(selected_label, user_prompt, ai_reply)
            st.success("Interaction saved to database.")

# Optional: View Database (for debugging/admin)
with st.expander("View Request History (Admin Only)"):
    st.json(load_history())