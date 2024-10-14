import logging
import os
import json
import zipfile
from adobe.pdfservices.operation.auth.credentials import Credentials
from adobe.pdfservices.operation.execution_context import ExecutionContext
from adobe.pdfservices.operation.io.file_ref import FileRef
from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)

class PDFExtract:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k")
        # Add the glossary map prompt
        self.glossary_map_template = """
        You are an AI assistant creating a glossary entry for a technical term or concept. Given the following content, please:

        1. Identify the main term or concept being discussed.
        2. Provide a clear and concise definition.
        3. Include any relevant additional information such as formulas, related concepts, or key characteristics.
        4. If the content isn't suitable for a glossary entry, respond with just the word "SKIP".

        Format your response as follows:
        TERM: [The identified term]
        DEFINITION: [Concise definition]
        DETAILS: [Any additional relevant information. If none, write "N/A"]

        Content:
        {context}

        Glossary Entry:
        """
        self.glossary_map_prompt = ChatPromptTemplate([("human", self.glossary_map_template)])
        self.glossary_map_chain = self.glossary_map_prompt | self.llm | StrOutputParser()

    def _get_credentials(self):
        credentials = Credentials.service_principal_credentials_builder().with_client_id(
            self.client_id).with_client_secret(self.client_secret).build()
        return credentials

    def _zip_file(self, output_path, unzip_dir):
        with zipfile.ZipFile(output_path, 'r') as zip_ref:
            zip_ref.extractall(unzip_dir)

    def _parse_json(self, json_file_path):
        with open(json_file_path, "r") as json_file:
            content = json.loads(json_file.read())
        pdf_element = content["elements"]
        return pdf_element

    def get_files_from_dir(self, dir):
        files = [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
        return files

    def load_docs(self, file_path):
        loader = TextLoader(file_path)
        docs = loader.load()
        return docs

    def parse_pdf(self, input_file_path, output_path, unzip_dir, chunked_dir):
        try:
            credentials = self._get_credentials()
            execution_context = ExecutionContext.create(credentials)
            extract_pdf_operation = ExtractPDFOperation.create_new()
            source = FileRef.create_from_local_file(input_file_path)
            extract_pdf_operation.set_input(source)
            extract_pdf_options = ExtractPDFOptions.builder().with_element_to_extract(ExtractElementType.TEXT).build()
            extract_pdf_operation.set_options(extract_pdf_options)

            result = extract_pdf_operation.execute(execution_context)
            result.save_as(output_path)
            self._zip_file(output_path, unzip_dir)
            json_file_path = os.path.join(unzip_dir, "structuredData.json")
            elements = self._parse_json(json_file_path)

            file_split = 0
            FIRST_TIME_HEADER = True
            file_name = os.path.join(chunked_dir, f"file_{file_split}.txt")
            parsed_file = open(file_name, "a", encoding="utf-8")
            for element in elements:
                if "//Document/H2" in element["Path"]:
                    hdr_txt = element["Text"]
                    if FIRST_TIME_HEADER:
                        FIRST_TIME_HEADER = False
                        parsed_file.write(hdr_txt)
                        parsed_file.write("\n")
                    else:
                        parsed_file.close()
                        file_split = file_split + 1
                        file_name = os.path.join(chunked_dir, f"file_{file_split}.txt")
                        parsed_file = open(file_name, "a", encoding="utf-8")
                        parsed_file.write(hdr_txt)
                        parsed_file.write("\n")
                else:
                    try:
                        text_content = element["Text"]
                        parsed_file.write(text_content)
                        parsed_file.write("\n")
                    except KeyError:
                        pass
            parsed_file.close()
            logging.info(f"PDF parsing completed. Chunks saved in '{chunked_dir}'.")
        except Exception as e:
            print(e)
            logging.exception("Exception encountered while executing operation")

    async def create_glossary(self, chunked_dir):
        glossary = {}
        files = self.get_files_from_dir(chunked_dir)
        
        async def process_document(file):
            docs = self.load_docs(file)
            for doc in docs:
                print(f"Processing document: {file}")
                
                response = await self.glossary_map_chain.ainvoke({"context": doc.page_content})
                
                if not response.strip().upper().startswith("SKIP"):
                    try:
                        lines = response.strip().split('\n')
                        term = lines[0].split('TERM:')[1].strip()
                        definition = lines[1].split('DEFINITION:')[1].strip()
                        details = lines[2].split('DETAILS:')[1].strip()
                        
                        glossary_entry = f"{definition}\n\nAdditional Details: {details}"
                        glossary[term] = glossary_entry
                        print(f"Generated glossary entry: {term}")
                    except IndexError:
                        print(f"Unexpected result format: {response}")
                else:
                    print(f"Skipped document: {file}")

        document_tasks = [process_document(file) for file in files]
        await asyncio.gather(*document_tasks)

        if glossary:
            output_file = os.path.join(chunked_dir, "technical_glossary.txt")
            with open(output_file, "w") as f:
                for term, entry in glossary.items():
                    f.write(f"{term}:\n{entry}\n")
                    f.write("-" * 40 + "\n")
            
            print(f"Technical glossary has been written to '{output_file}'")
        else:
            print("No glossary entries were generated as all documents were skipped.")

        return glossary