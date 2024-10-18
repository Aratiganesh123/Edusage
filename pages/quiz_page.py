import streamlit as st
import os
import sys
from io import BytesIO

# Add the parent directory to sys.path to allow importing from modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.quiz import process_document, generate_quiz, QuizMultipleChoice, QuizTrueFalse, QuizOpenEnded

def show_quiz_page():
    st.header("Quiz Generator")

    # Custom CSS for the info box
    st.markdown("""
    <style>
    .stInfo {
        background-color: #E6F3FF;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #3498DB;
        margin-bottom: 20px;
    }
    .stInfo p {
        color: #2C3E50;
        font-size: 16px;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

    # Info box with concise description
    st.info("""
    📚 **Quick Guide:**
    1. Upload your PDF
    2. Set quiz parameters
    3. Generate and take the quiz
    4. Review your score

    Perfect for self-study and exam prep!
    """)

    # Initialize session state variables
    if 'quiz_generated' not in st.session_state:
        st.session_state.quiz_generated = False
    if 'uploaded_file_content' not in st.session_state:
        st.session_state.uploaded_file_content = None
    if 'chunks' not in st.session_state:
        st.session_state.chunks = None
    if 'quiz_type' not in st.session_state:
        st.session_state.quiz_type = None
    if 'quiz_data' not in st.session_state:
        st.session_state.quiz_data = None
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = []

    uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])

    if uploaded_file is not None:
        st.session_state.uploaded_file_content = uploaded_file.getvalue()

    if st.session_state.uploaded_file_content is not None and st.session_state.chunks is None:
        with st.spinner("Processing document..."):
            file_content = BytesIO(st.session_state.uploaded_file_content)
            file_content.name = uploaded_file.name  # Use the original file name
            chunks = process_document(file_content)
            st.session_state.chunks = chunks  # Store chunks for later use
            if chunks:
                st.success("Document processed successfully!")
            else:
                st.error("Failed to process document.")

    if st.session_state.chunks is not None and not st.session_state.quiz_generated:
        # Quiz parameters
        num_questions = st.slider("Number of questions", 1, 10, 5)
        quiz_type = st.selectbox("Quiz type", ["Multiple Choice", "True/False", "Open Ended"])

        if st.button("Generate Quiz"):
            quiz_data = generate_quiz(st.session_state.chunks, num_questions, quiz_type)
            st.session_state.quiz_data = quiz_data
            st.session_state.quiz_generated = True
            st.session_state.quiz_type = quiz_type
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.session_state.user_answers = []
            st.rerun()

    if st.session_state.quiz_generated:
        display_quiz()


def display_quiz():
    quiz_data = st.session_state.quiz_data
    quiz_type = st.session_state.quiz_type
    current_question = st.session_state.current_question
    num_questions = len(quiz_data.questions)

    if current_question < num_questions:
        st.subheader(f"Question {current_question + 1}")
        question_text = quiz_data.questions[current_question]
        st.write(question_text)

        user_answer = None
        if quiz_type == "Multiple Choice":
            options = quiz_data.alternatives[current_question]
            user_answer = st.radio("Choose your answer:", options, key=f"q{current_question}")
        elif quiz_type == "True/False":
            user_answer = st.radio("Choose your answer:", ["True", "False"], key=f"q{current_question}")
        else:  # Open Ended
            user_answer = st.text_input("Your answer:", key=f"q{current_question}")

        if st.button("Submit Answer", key=f"submit{current_question}"):
            check_answer(quiz_data, quiz_type, current_question, user_answer)
            st.session_state.current_question += 1
            st.rerun()
    else:
        show_quiz_results()

def check_answer(quiz_data, quiz_type, current_question, user_answer):
    correct_answer = quiz_data.answers[current_question]
    st.session_state.user_answers.append(user_answer)
    if quiz_type == "Multiple Choice":
        options = quiz_data.alternatives[current_question]
        correct_option = options[ord(correct_answer.upper()) - ord('A')]
        if user_answer.strip().lower() == correct_option.strip().lower():
            st.success("Correct!")
            st.session_state.score += 1
        else:
            st.error(f"Incorrect. The correct answer is: {correct_option}")
    elif quiz_type == "True/False":
        if user_answer.strip().lower() == correct_answer.strip().lower():
            st.success("Correct!")
            st.session_state.score += 1
        else:
            st.error(f"Incorrect. The correct answer is: {correct_answer}")
    else:  # Open Ended
        st.write(f"Your answer: {user_answer}")
        st.write(f"Correct answer: {correct_answer}")
        st.write("Please compare your answer to the correct answer.")
        if st.button("Mark as Correct", key=f"mark{current_question}"):
            st.success("Marked as correct!")
            st.session_state.score += 1
        else:
            st.error("Marked as incorrect.")

def show_quiz_results():
    st.subheader("Quiz Completed!")
    st.write(f"Your final score: {st.session_state.score} out of {len(st.session_state.quiz_data.questions)}")
    if st.button("Start New Quiz"):
        # Reset only quiz-related variables
        st.session_state.quiz_generated = False
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.user_answers = []
        st.session_state.quiz_data = None
        st.session_state.quiz_type = None
        st.session_state.num_questions = None
        st.rerun()

def main():
    show_quiz_page()

if __name__ == "__main__":
    main()