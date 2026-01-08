import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import json
import re

# --- Configuration ---
st.set_page_config(page_title="YouTube Quiz Generator", layout="centered")

# --- Authentication Logic ---
# Check if the API key is in Streamlit Secrets (server-side security)
api_key = None

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # If not in secrets, ask the user for it
    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("Enter Gemini API Key", type="password")
        st.caption("Get a free key at aistudio.google.com")

# Configure Gemini if key is present
if api_key:
    genai.configure(api_key=api_key)
else:
    # Stop the app here if no key is available
    st.warning("Please enter an API key in the sidebar to proceed.")
    st.stop()

# --- Helper Functions ---

def get_video_id(url):
    """Extracts the video ID from a YouTube URL."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    """Fetches the transcript of the video."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return transcript_text
    except Exception as e:
        return None

def generate_quiz(transcript_text, num_questions=5):
    """Prompts Gemini to generate a quiz from the text."""
    
    prompt = f"""
    You are a teacher. Create a multiple-choice quiz based on the following transcript.
    
    Transcript:
    "{transcript_text}"

    Generate {num_questions} questions.
    
    Requirements:
    1. Output MUST be a raw JSON list of objects.
    2. Do NOT use markdown code blocks (like ```json). Just the raw JSON.
    3. Each object must have:
       - "question": The question string
       - "options": A list of 4 possible answers
       - "answer": The correct answer string (must match one of the options exactly)
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return []

# --- Main UI ---

st.title("🎥 YouTube to Quiz")
st.write("Test your knowledge on any YouTube video.")

# 1. Input URL
video_url = st.text_input("YouTube Video URL", placeholder="[https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=)...")

if video_url:
    video_id = get_video_id(video_url)
    
    if video_id:
        st.video(video_url)
        
        if st.button("Generate Quiz"):
            with st.spinner("Fetching transcript and asking Gemini..."):
                transcript = get_transcript(video_id)
                
                if transcript:
                    st.session_state['quiz_data'] = generate_quiz(transcript)
                    st.session_state['user_answers'] = {}
                else:
                    st.error("Could not retrieve transcript. The video might not have captions enabled.")

# 2. Display Quiz
if 'quiz_data' in st.session_state and st.session_state['quiz_data']:
    st.markdown("---")
    st.subheader("🧠 Quiz Time")
    
    with st.form(key='quiz_form'):
        quiz_data = st.session_state['quiz_data']
        
        for i, q in enumerate(quiz_data):
            st.markdown(f"**{i+1}. {q['question']}**")
            choice = st.radio(
                "Choose an answer:", 
                q['options'], 
                key=f"q_{i}", 
                index=None
            )
            st.session_state['user_answers'][i] = choice
            st.markdown("---")
            
        submit_button = st.form_submit_button(label="Submit Answers")

        if submit_button:
            st.success("Quiz Submitted!")
            correct_count = 0
            for i, q in enumerate(quiz_data):
                user_choice = st.session_state['user_answers'].get(i)
                correct_answer = q['answer']
                
                if user_choice == correct_answer:
                    correct_count += 1
                    st.write(f"✅ Question {i+1}: Correct!")
                else:
                    st.write(f"❌ Question {i+1}: Incorrect. You chose **{user_choice}**. The correct answer was **{correct_answer}**.")
            
            st.metric(label="Final Score", value=f"{correct_count} / {len(quiz_data)}")