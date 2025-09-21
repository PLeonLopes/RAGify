import streamlit as st
from dotenv import load_dotenv
import os

from langchain_core.messages import HumanMessage, AIMessage

from werkzeug.security import check_password_hash, generate_password_hash

from html_templates import css, user_template, bot_template
import database
from utils import extract_text_from_files, get_text_chunks, get_conversation_chain, get_vectorstore
from ui_handlers import display_auth_ui, handle_user_input, display_uploaded_files_ui, handle_file_removal_logic

FAISS_INDEX_NAME = "index"          # FAISS index (Const)

def main():
    load_dotenv()
    st.set_page_config(page_title="RAGify - Chat", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state: st.session_state.conversation = None
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "vectorstore_loaded_for_user" not in st.session_state: st.session_state.vectorstore_loaded_for_user = False
    if "processed_files_session" not in st.session_state: st.session_state.processed_files_session = []

    display_auth_ui()           # Sign UP/Login Sidear -> ui_handlers

    if st.session_state.get("logged_in_user_id") and (st.session_state.conversation is None or not st.session_state.vectorstore_loaded_for_user):
        with st.spinner("Carregando dados do usuário..."):
            user_id = st.session_state.logged_in_user_id
            loaded_chat_history_messages = []
            db_history_tuples = database.load_chat_history(user_id)
            if db_history_tuples:
                for u_msg, ai_msg in db_history_tuples:
                    if u_msg: loaded_chat_history_messages.append(HumanMessage(content=u_msg))
                    if ai_msg: loaded_chat_history_messages.append(AIMessage(content=ai_msg))
            st.session_state.chat_history = loaded_chat_history_messages 

            # VectorStore usage
            vectorstore = get_vectorstore(
                user_id=user_id, db_get_user_faiss_path_func=database.get_user_faiss_path,
                faiss_index_name_const=FAISS_INDEX_NAME, session_state=st.session_state, st_feedback_obj=st
            )
            if vectorstore:
                st.session_state.conversation = get_conversation_chain(vectorstore, initial_chat_history=st.session_state.chat_history)
                
                if not st.session_state.vectorstore_loaded_for_user : 
                     st.success("Conhecimento anterior carregado. Pronto para conversar!")
                st.session_state.vectorstore_loaded_for_user = True
            else:
                st.session_state.vectorstore_loaded_for_user = False

    st.header("RAGify - Ask questions about your documents")
    
    # IF chat_history
    if st.session_state.chat_history:
        st.subheader("Chat History:")
        # Shows chat history, using template (html_templates.py)
        for i, message in enumerate(st.session_state.chat_history):
            msg_content = getattr(message, 'content', str(message))
            if isinstance(message, HumanMessage) or (i % 2 == 0 and not isinstance(message, AIMessage)):            # USER message
                st.write(user_template.replace("{{MSG}}", msg_content), unsafe_allow_html=True)
            elif isinstance(message, AIMessage) or (i % 2 != 0):                                                    # LLM message
                st.write(bot_template.replace("{{MSG}}", msg_content), unsafe_allow_html=True)
        st.markdown("---")

    # User Input
    with st.form(key="chat_input_form", clear_on_submit=True):
        user_question_typed = st.text_input("Ask a question about your documents:", key="user_question_input_field")
        submitted = st.form_submit_button("Send")

    # Processing the questionn 
    if submitted and user_question_typed: 
        if st.session_state.conversation:
            with st.spinner("Thinking... 🧠"):
                handle_user_input(
                    user_question_typed,
                    get_conversation_chain_func=get_conversation_chain,
                    save_chat_message_func=database.save_chat_message
                )
            st.rerun() 
        else:
            st.warning("Please upload some files or log in to load your knowledge.")

    # Sidebar (File upload)
    with st.sidebar:
        uploader_key = f"file_uploader_{st.session_state.get('logged_in_user_id', 'guest')}"
        
        pdf_docs = st.file_uploader(
            "Upload new files and click Process",
            accept_multiple_files=True,
            type=["pdf", "docx", "xlsx", "csv", "txt", "md"],
            key=uploader_key
        )

        # Processing of new files
        if st.button("Process Files 📂", key="process_button"):
            if pdf_docs:
                with st.spinner("Processing Files... ⚙️"):
                    current_user_id = st.session_state.get("logged_in_user_id")
                    if not current_user_id:
                        st.session_state.processed_files_session = [] 
                        for doc in pdf_docs:
                            doc_bytes = doc.getvalue() 
                            st.session_state.processed_files_session.append(
                                {'name': doc.name, 'id': doc.name, 'bytes': doc_bytes}
                            )
                            doc.seek(0)
                    
                    raw_text = extract_text_from_files(pdf_docs)
                    text_chunks = []

                    if not raw_text or not raw_text.strip():
                        st.warning("No text extracted from the files. Check the formats or content.")            # File format no supported
                    else:
                        text_chunks = get_text_chunks(raw_text)

                    # VectorStore usage                                  
                    vectorstore = get_vectorstore(
                        text_chunks=text_chunks if text_chunks else None, 
                        user_id=current_user_id,
                        db_get_user_faiss_path_func=database.get_user_faiss_path,
                        faiss_index_name_const=FAISS_INDEX_NAME,
                        session_state=st.session_state,
                        st_feedback_obj=st
                    )

                    if vectorstore: 
                        chat_hist_for_chain = [] 
                        if current_user_id: 
                            db_history_tuples = database.load_chat_history(current_user_id)         # conversation_chain fetching chat history
                            if db_history_tuples:
                                for u_msg, ai_msg in db_history_tuples:
                                    if u_msg: chat_hist_for_chain.append(HumanMessage(content=u_msg))           # USER messages
                                    if ai_msg: chat_hist_for_chain.append(AIMessage(content=ai_msg))            # LLM messages
                        st.session_state.chat_history = chat_hist_for_chain
                        
                        st.session_state.conversation = get_conversation_chain(
                            vectorstore, initial_chat_history=st.session_state.chat_history
                        )
                        st.session_state.vectorstore_loaded_for_user = True
                        
                        if current_user_id:
                            user_faiss_dir_path = database.get_user_faiss_path(current_user_id)
                            # Add it to DB
                            for doc in pdf_docs: 
                                database.add_user_file_record(current_user_id, doc.name, user_faiss_dir_path)
                            st.success("Files processed and knowledge saved/updated!")
                        else:
                            st.success("Files processed for this session!")
                        st.rerun()
                    elif current_user_id and not text_chunks and \
                         not (database.get_user_faiss_path(current_user_id) and \
                              os.path.exists(os.path.join(database.get_user_faiss_path(current_user_id), f"{FAISS_INDEX_NAME}.faiss"))):
                         st.warning("No text processed from the files and no previous knowledge found.")
                         st.session_state.conversation = None 
                         st.session_state.vectorstore_loaded_for_user = False
                    elif current_user_id and not text_chunks: 
                        st.info("No new files processed. Previous knowledge (if any) is active.")
                    else: 
                        if not current_user_id and not text_chunks:                     # User logged in without text (edge-case)
                             st.warning("No text available for this session.")
                        else:
                            st.error("There was a failure creating or loading the vector knowledge base. Please try again later.")
                        st.session_state.conversation = None
                        st.session_state.vectorstore_loaded_for_user = False
            else:
                st.warning("Please upload at least one file.")
        
        # UI to display uploaded files (using helper functions) -> Refactor ASAP! 
        display_uploaded_files_ui(handle_file_removal_func=lambda file_id, file_name, source: handle_file_removal_logic(
                file_id, file_name, source, FAISS_INDEX_NAME,
                lambda **kwargs: get_vectorstore(
                    db_get_user_faiss_path_func=database.get_user_faiss_path,
                    faiss_index_name_const=FAISS_INDEX_NAME,
                    session_state=st.session_state,
                    st_feedback_obj=st,
                    **kwargs
                ), 
                get_conversation_chain 
            ),
            faiss_index_name_const=FAISS_INDEX_NAME
        )

if __name__ == '__main__':
    main()