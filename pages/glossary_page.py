import streamlit as st
import os
import tempfile
import sys
import asyncio

# Add the parent directory to sys.path to allow importing from modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.glossary import PDFExtract

async def process_pdf_for_glossary(pdf_extract, tmp_file_path, output_dir, unzip_dir, chunked_dir):
    with st.spinner("Parsing PDF..."):
        pdf_extract.parse_pdf(tmp_file_path, os.path.join(output_dir, "extracted.zip"), unzip_dir, chunked_dir)
    st.success("PDF parsed successfully!")

    with st.spinner("Extracting glossary terms..."):
        glossary = await pdf_extract.create_glossary(chunked_dir)
    st.success("Glossary terms extracted successfully!")

    return glossary

async def show_glossary_page():
    st.header("Glossary Extractor")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        st.success("File uploaded successfully!")

        if st.button("Extract Glossary"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            output_dir = tempfile.mkdtemp()
            unzip_dir = os.path.join(output_dir, "unzipped")
            chunked_dir = os.path.join(output_dir, "chunks")
            os.makedirs(unzip_dir)
            os.makedirs(chunked_dir)

            pdf_extract = PDFExtract(os.getenv("PDF_SERVICES_CLIENT_ID"), os.getenv("PDF_SERVICES_CLIENT_SECRET"))

            glossary = await process_pdf_for_glossary(pdf_extract, tmp_file_path, output_dir, unzip_dir, chunked_dir)

            st.subheader("Extracted Glossary Terms")
            for term, definition in glossary.items():
                with st.expander(term):
                    st.write(definition)

            # Clean up the temporary file
            os.unlink(tmp_file_path)

    else:
        st.info("Please upload a PDF file to begin.")

def main():
    asyncio.run(show_glossary_page())

if __name__ == "__main__":
    main()