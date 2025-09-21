import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
import openpyxl
import csv
import io

from langchain.text_splitter import CharacterTextSplitter
from langchain_community.chat_models import ChatOllama
from langchain.embeddings import HuggingFaceEmbeddings          # nomic-embed
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

from html_templates import css, user_template, bot_template

# Data Collection (Multiple Files -> text)
def extract_text_from_files(uploaded_files):

    text = ""
    for file in uploaded_files:
        filename = file.name.lower()

        # .pdf extraction
        if filename.endswith(".pdf"):
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

        # .docx extraction
        elif filename.endswith(".docx"):
            doc = Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        
        # .xlsx extraction
        elif filename.endswith(".xlsx"):
            wb = openpyxl.load_workbook(file, data_only=True)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    text += ' '.join([str(cell) if cell is not None else '' for cell in row]) + "\n"
        
        # .csv extraction
        elif filename.endswith(".csv"):
            decoded = file.read().decode("utf-8")
            reader = csv.reader(io.StringIO(decoded))
            for row in reader:
                text += ' | '.join(row) + "\n"

        # .txt/.md extraction
        elif filename.endswith(".txt") or filename.endswith(".md"):
            text += file.read().decode("utf-8") + "\n"

        else:
            text += f"\n[Unsupported file format: {file.name}]\n"
    return text


# Data chunking
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len)
    chunks = text_splitter.split_text(text)
    return chunks


# Document embeddings / "Vectorstore" creation (FAISS)
def get_vectorstore(text_chunks):
    embeddings = HuggingFaceEmbeddings(model_name="nomic-ai/nomic-embed-text-v1", model_kwargs={"trust_remote_code": True})         # Using nomic-embed-text-v1
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)

    return vectorstore


# "Conversation Chain" creation
def get_conversation_chain(vectorstore):

    llm = ChatOllama(model="llama3", temperature=0.1)           # Using llama3

    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)          # Conversation Memory

    # Prompt Template
    CUSTOM_PROMPT_TEMPLATE = """
    You are a highly specialized AI assistant, tasked with answering questions based on documents provided by the user.
    Your goal is to provide **accurate**, **clear**, and **strictly information-based answers** extracted from the uploaded files.
    If the answer cannot be found in the documents, **admit that you do not know** rather than inventing a response.
    You may use information from multiple documents. If the information is not directly connected, state this clearly.
    Always respond in **English**, even if the documents or the question are in another language.
    ---
    Conversation history:
    {chat_history}

    User question:
    {question}

    Document context:
    {context}

    Answer:
    """

    prompt = PromptTemplate(
        template=CUSTOM_PROMPT_TEMPLATE,
        input_variables=["chat_history", "question", "context"]
    )
    
    conversation_chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=vectorstore.as_retriever(), memory=memory, combine_docs_chain_kwargs={"prompt": prompt})
    return conversation_chain


def handle_userInput(user_question):
    response = st.session_state.conversation({'question' : user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

 
def main():
    load_dotenv()

    st.set_page_config(page_title="RAGify - Chat", page_icon=":books:")

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.write(css, unsafe_allow_html=True)

    st.header("RAGify - Multiple Files :books:")
    user_question = st.text_input("Ask a question about your documents: ")
    if user_question:
        handle_userInput(user_question)

    with st.sidebar:
        st.subheader("Your files: ")

        docs = st.file_uploader("Upload your documents and click Process (.pdf, .docx, .xlsx, .csv, .txt, .md)", accept_multiple_files=True)

        if st.button("Process"):
            with st.spinner("Processing"):
                # gets pdf text
                raw_text = extract_text_from_files(docs)

                # get text chunks
                text_chunks = get_text_chunks(raw_text)

                # Embeddings / Vectorstore (FAISS)
                vectorstore = get_vectorstore(text_chunks)
                
                # Creates "conversation chain"
                st.session_state.conversation = get_conversation_chain(vectorstore)

if __name__ == '__main__':
    main()