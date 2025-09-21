import streamlit as st
import os
import io

import database
from utils import extract_text_from_files, get_text_chunks

# UI Sign Up/Login
def display_auth_ui():
    if "logged_in_user_id" not in st.session_state:
        st.session_state.logged_in_user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    if st.session_state.logged_in_user_id is None:
        st.sidebar.subheader("Login ou Sign Up")

        with st.sidebar.form(key="auth_form_sidebar"):
            username_input = st.text_input("User", key="auth_username")
            password_input = st.text_input("Password", type="password", key="auth_password")
            
            # Sign Up/Login Buttons
            col1, col2 = st.columns(2)
            login_button = col1.form_submit_button("Login")
            create_account_button = col2.form_submit_button("Sign Up")

            # Login Button
            if login_button:
                from werkzeug.security import check_password_hash

                user = database.get_user(username_input)
                
                if user and check_password_hash(user["password_hash"], password_input):
                    st.session_state.logged_in_user_id = user["id"]
                    st.session_state.username = user["username"]
                    st.sidebar.success(f"Login as: {st.session_state.username}")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password.")

            # Sign Up button
            if create_account_button:
                if username_input and password_input:
                    existing_user = database.get_user(username_input)
                    if existing_user:
                        st.sidebar.warning("User already Exists.")
                    else:
                        from werkzeug.security import generate_password_hash
                        
                        hashed_password = generate_password_hash(password_input)
                        user_id = database.add_user(username_input, hashed_password)

                        if user_id:
                            st.sidebar.success("Account created! Please log in.")
                        else:
                            st.sidebar.error("Error creating account.")
                else:
                    st.sidebar.warning("Fill in username and password.")
    else:
        st.sidebar.subheader(f"Logged in as: {st.session_state.username}")
        if st.sidebar.button("Logout", key="logout_button_sidebar"):
            for key in list(st.session_state.keys()):
                if key in ["logged_in_user_id", "username", "conversation", "chat_history", "vectorstore_loaded_for_user", "processed_files_session"]:
                    if key in st.session_state:
                        del st.session_state[key]
            st.sidebar.info("Logout successful.")
            st.rerun()

# Processes user question, interactss with conversation_chain and FAISS
def handle_user_input(user_question, get_conversation_chain_func, save_chat_message_func):
    
    if "conversation" not in st.session_state or st.session_state.conversation is None:
        st.warning("Please process some files first or check if the knowledge has been loaded.")
        return

    # conversation_chain called by (st.session_state.conversation)
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history'] 

    if st.session_state.get("logged_in_user_id") and len(st.session_state.chat_history) >= 2:
        if hasattr(st.session_state.chat_history[-2], 'content') and hasattr(st.session_state.chat_history[-1], 'content'):
            last_user_msg = st.session_state.chat_history[-2].content
            last_ai_msg = st.session_state.chat_history[-1].content
            save_chat_message_func(st.session_state.logged_in_user_id, last_user_msg, last_ai_msg)

# UI to display files in the sidebar
def display_uploaded_files_ui(handle_file_removal_func, faiss_index_name_const):
    
    user_id = st.session_state.get("logged_in_user_id")
    files_to_display = []           # Files list

    if user_id:         # IF logged in
        db_files = database.get_user_files(user_id)
        for db_file in db_files:
            files_to_display.append({'id': db_file['id'], 'name': db_file['filename'], 'source': 'db'})
    else:               # IF NOT logged in (session)
        for session_file in st.session_state.get("processed_files_session", []):
            files_to_display.append({'id': session_file['name'], 'name': session_file['name'], 'source': 'session'})

    if not files_to_display:
        st.sidebar.info("No files loaded yet.")
        return

    st.sidebar.subheader("Files loaded:")
    for file_info in files_to_display:
        col1, col2 = st.sidebar.columns([4, 1])
        col1.write(file_info['name'])

        button_key = f"remove_{file_info['source']}_{str(file_info['id']).replace('.', '_').replace(' ', '_')}"
        
        # Files removal
        if col2.button("🗑️", key=button_key, help=f"Remover {file_info['name']}"):
            handle_file_removal_func(file_info['id'], file_info['name'], file_info['source'], faiss_index_name_const)           # Auxiliary Function
            st.rerun()

# Auxiliary function to handle file removal logic
def handle_file_removal_logic(file_identifier, file_name_for_display, source, faiss_index_name_const, get_vectorstore_func, get_conversation_chain_func):
    
    user_id = st.session_state.get("logged_in_user_id")

    # IF user logged in, data -> DB
    if source == 'db' and user_id:
        if database.delete_user_file(file_identifier):
            st.sidebar.success(f"File '{file_name_for_display}' successfully removed!")
            
            user_faiss_dir_path = database.get_user_faiss_path(user_id)
            faiss_file_path = os.path.join(user_faiss_dir_path, f"{faiss_index_name_const}.faiss")          # .faiss index
            pkl_file_path = os.path.join(user_faiss_dir_path, f"{faiss_index_name_const}.pkl")              # .pkl index/file
            
            if os.path.exists(faiss_file_path): os.remove(faiss_file_path)
            if os.path.exists(pkl_file_path): os.remove(pkl_file_path)
            
            st.warning("Your knowledge base has been cleared. Please process the desired files again!")
            st.session_state.conversation = None
            st.session_state.chat_history = []
            st.session_state.vectorstore_loaded_for_user = False
        else:
            st.sidebar.error(f"Error removing '{file_name_for_display}' from the record.")

    # IF user NOT logged in, data -> session
    elif source == 'session' and not user_id:
        st.session_state.processed_files_session = [
            f for f in st.session_state.processed_files_session if f['name'] != file_identifier
        ]
        st.sidebar.success(f"File '{file_name_for_display}' removed from Session.")

        if not st.session_state.processed_files_session:
            st.session_state.conversation = None
            st.session_state.chat_history = []
            st.info("All session files have been removed!")
        else:
            with st.spinner("Updating session knowledge..."):
                mock_uploaded_files = []
                for file_data in st.session_state.processed_files_session:
                    bytes_io_obj = io.BytesIO(file_data['bytes'])
                    bytes_io_obj.name = file_data['name'] 
                    mock_uploaded_files.append(bytes_io_obj)

                raw_text = extract_text_from_files(mock_uploaded_files) 
                if raw_text and raw_text.strip():
                    text_chunks = get_text_chunks(raw_text) 
                    vectorstore = get_vectorstore_func(text_chunks=text_chunks, user_id=None)
                    if vectorstore:
                        st.session_state.conversation = get_conversation_chain_func(vectorstore, initial_chat_history=[]) 
                        st.session_state.chat_history = []
                        st.success("Session knowledge updated.")
                    else:
                        st.session_state.conversation = None; st.session_state.chat_history = []
                        st.error("Failed to rebuild session knowledge.")
                else:
                    st.session_state.conversation = None; st.session_state.chat_history = []
                    st.info("No text to process after removal.")
    else:
        st.error("Error: Inconsistent state when trying to remove file.")