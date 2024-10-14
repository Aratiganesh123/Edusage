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
        self.map_template = """
        Analyze the following content and create a structured summary:

        1. Identify the main topic or heading.
        2. Provide 3-5 key points that explain the core ideas, techniques, or methodologies.
        3. Use bullet points for the key points.
        4. Include relevant formulas or mathematical notations if applicable.
        5. If the content is not substantive or doesn't contain important information, respond with "SKIP".

        Format your response as follows:
        Main Topic: [Identified main topic or heading]

        • [Key point 1]
        • [Key point 2]
        • [Key point 3]
        [Add more bullet points if necessary]

        Content:
        {context}

        Summary:
        """
        self.map_prompt = ChatPromptTemplate([("human", self.map_template)])
        self.map_chain = self.map_prompt | self.llm | StrOutputParser()

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

    async def generate_summary(self, content):
        response = await self.map_chain.ainvoke({"context": content})
        return response

    async def process_documents(self, list_of_all_docs, output_dir):
        summaries = []
        for i, doc in enumerate(list_of_all_docs, 1):
            print(f"Processing document {i}/{len(list_of_all_docs)}")
            
            response = await self.generate_summary(doc.page_content)
            
            if response.strip().upper() != "SKIP":
                summaries.append(f"Document {i}:\n\n{response}\n\n{'='*50}\n\n")
                print(f"Generated summary for document {i}")
            else:
                print(f"Skipped summarizing document {i}")

        if summaries:
            output_file = os.path.join(output_dir, "technical_summaries.txt")
            with open(output_file, "w") as f:
                f.writelines(summaries)
            
            print(f"All technical summaries have been written to '{output_file}'")
        else:
            print("No summaries were generated as all documents were skipped.")

        return summaries