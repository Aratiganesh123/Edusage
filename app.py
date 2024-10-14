import streamlit as st
import asyncio
from pages.summarizer_page import show_summarizer_page
from pages.glossary_page import show_glossary_page

def style_app():
    st.markdown(
        """
        <style>
        .main {
            background-color: #2C3E50;
            color: #ECF0F1;
            font-size: 18px;
        }
        .sidebar .sidebar-content {
            background-color: #34495E;
        }
        .stButton>button {
            background-color: #3498DB;
            color: white;
            border: none;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 18px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 5px;
            transition: background-color 0.3s;
        }
        .stButton>button:hover {
            background-color: #2980B9;
        }
        h1 {
            color: #FF6B6B;
            font-size: 48px;
        }
        h2 {
            color: #FFD93D;
            font-size: 36px;
        }
        .stTextInput>div>div>input {
            background-color: #ECF0F1;
            color: #2C3E50;
            font-size: 18px;
        }
        .stSelectbox>div>div>select {
            font-size: 18px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

async def main():
    st.set_page_config(page_title="Edusage", page_icon="📚", layout="wide")
    style_app()

    st.sidebar.title("📚 Edusage Navigation")
    st.sidebar.markdown("---")
    page = st.sidebar.selectbox("Choose a Mode 🔽", ["🏠 Home", "📝 PDF Summarizer", "📖 Glossary Extractor", "🤖 Chatbot", "❓ Quiz"])

    if page == "🏠 Home":
        st.title("🎓 Welcome to Edusage")
        st.write("""
            Edusage is your all-in-one educational tool for working with PDF documents. 
            Use our features to summarize content, extract glossary terms, interact with a chatbot, and test your knowledge.
            
            To get started, select a mode from the dropdown menu in the sidebar on the left.
        """)
        
        st.header("📤 Upload Your PDF")
        uploaded_file = st.file_uploader("Drag and drop your PDF file here", type="pdf")
        if uploaded_file is not None:
            st.success("✅ File uploaded successfully! Choose a mode from the sidebar to analyze it.")
        
    elif page == "📝 PDF Summarizer":
        await show_summarizer_page()
    elif page == "📖 Glossary Extractor":
        await show_glossary_page()

if __name__ == "__main__":
    asyncio.run(main())