import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import List
from langchain.pydantic_v1 import BaseModel, Field
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
import tempfile

load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = "quiz-index"

# Define quiz data models
class QuizTrueFalse(BaseModel):
    questions: List[str] = Field(description="The quiz questions")
    answers: List[str] = Field(description="The correct answers for each question (True or False)")

class QuizMultipleChoice(BaseModel):
    questions: List[str] = Field(description="The quiz questions")
    alternatives: List[List[str]] = Field(description="The options for each question")
    answers: List[str] = Field(description="The correct answers for each question (e.g., 'A', 'B', 'C', 'D')")

class QuizOpenEnded(BaseModel):
    questions: List[str] = Field(description="The quiz questions")
    answers: List[str] = Field(description="The correct answers for each question")

def generate_quiz_prompt():
    template = """
    You are an expert quiz maker specializing in highly technical and conceptual questions.
    Generate a {num_questions}-question {quiz_type} quiz based on the following context:

    {context}

    Critical guidelines:
    1. Focus exclusively on technical concepts, theories, algorithms, methodologies, and specific technical details from the text.
    2. Ensure each question covers a different concept or section from the context to avoid repetition.
    3. Do not ask about conferences, authors, publication dates, or general themes.
    4. Questions must require deep understanding of technical subject matter.
    5. For multiple-choice questions, all options should be technical in nature and closely related to the core concept.
    6. Open-ended questions should demand specific technical explanations or problem-solving.
    7. Prefer questions that involve application of concepts, analysis of technical scenarios, or comparison of methodologies.
    8. If the context doesn't provide enough technical depth for a question, generate fewer questions rather than include non-technical ones.

    Provide the quiz in JSON format matching the following schema:

    Multiple Choice Quiz Schema:
    {{
    "questions": [List of highly technical concept questions],
    "alternatives": [List of technically relevant options for each question],
    "answers": [List of correct answers (e.g., 'A', 'B', 'C', 'D')]
    }}

    True/False Quiz Schema:
    {{
    "questions": [List of technical statement questions],
    "answers": [List of correct answers ('True' or 'False')]
    }}

    Open Ended Quiz Schema:
    {{
    "questions": [List of questions requiring specific technical answers],
    "answers": [List of correct technical answers]
    }}

    Ensure that the output is valid JSON and matches the schema exactly. Do not include any additional text or explanations.
    """
    return PromptTemplate(template=template, input_variables=['num_questions', 'quiz_type', 'context'])

def create_quiz_chain(prompt_template, llm, quiz_schema):
    return prompt_template | llm.with_structured_output(quiz_schema)

def load_document(file):
    file_extension = os.path.splitext(file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(file.read())
        tmp_file_path = tmp_file.name
        if file_extension == ".pdf":
            loader = PyPDFLoader(tmp_file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    return loader

def process_document(file):
    loader = load_document(file)
    pages = loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(pages)
    return texts

def generate_quiz(chunks, num_questions, quiz_type):
    # Build the context by selecting non-overlapping chunks
    if not chunks:
        raise ValueError("No chunks available for context.")

    # Calculate the number of chunks needed
    num_chunks_needed = num_questions
    chunk_indices = list(range(len(chunks)))

    # Select chunks sequentially to cover different parts
    step = max(1, len(chunk_indices) // num_questions)
    selected_indices = chunk_indices[::step][:num_questions]
    selected_chunks = [chunks[i] for i in selected_indices]
    combined_context = " ".join([chunk.page_content for chunk in selected_chunks])

    # Limit the context size to avoid exceeding token limits
    max_context_length = 3000  # Adjust based on model limits
    if len(combined_context) > max_context_length:
        combined_context = combined_context[:max_context_length]

    prompt_template = generate_quiz_prompt()
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

    # Select the appropriate Pydantic model output schema based on the quiz
    if quiz_type == "Multiple Choice":
        quiz_schema = QuizMultipleChoice
    elif quiz_type == "True/False":
        quiz_schema = QuizTrueFalse
    else:
        quiz_schema = QuizOpenEnded

    chain = create_quiz_chain(prompt_template, llm, quiz_schema)

    response = chain.invoke({
        'num_questions': num_questions,
        'quiz_type': quiz_type,
        'context': combined_context
    })

    return response