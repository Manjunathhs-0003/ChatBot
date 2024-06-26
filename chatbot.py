import os
import random
import aiohttp
import asyncio
import spacy
from dotenv import load_dotenv
from rapidfuzz import process, fuzz
import streamlit as st

load_dotenv()

api_key = os.getenv("api_key")
azure_endpoint = os.getenv("azure_endpoint")
api_version = "2024-02-15-preview"

nlp = spacy.load("en_core_web_sm")

# read topics from a file
def read_topics_from_file(file_path):
    with open(file_path, 'r') as file:
        topics = file.read().splitlines()
    return [topic.strip().lower() for topic in topics]

# read blog links from a file
def read_blog_links_from_file(file_path):
    blogs = {}
    with open(file_path, 'r') as file:
        for line in file:
            topic, links = line.strip().split('|')
            blogs[topic.strip().lower()] = [link.strip() for link in links.split(',') if link.strip()]
    return blogs

# correct spellings
def correct_spelling(question, topics):
    words = question.split()
    corrected_words = []
    for word in words:
        best_match, score, _ = process.extractOne(word, topics, scorer=fuzz.ratio)
        if score > 80:  # Adjust the threshold as needed
            corrected_words.append(best_match)
        else:
            corrected_words.append(word)
    return ' '.join(corrected_words)

# get related topic
def get_related_topic(question, topics):
    question_lower = question.lower()
    for topic in topics:
        if topic in question_lower:
            return topic
    return None

# select a random blog link
def select_random_blog_link(topic, blogs):
    if topic in blogs:
        return random.choice(blogs[topic])
    else:
        print(f"No blogs found for topic: {topic}")
        return None

topics_file_path = "topics.txt"
blogs_file_path = "blogs.txt"

topics = read_topics_from_file(topics_file_path)
blogs = read_blog_links_from_file(blogs_file_path)

async def get_response(session, question):
    headers = {
        'Content-Type': 'application/json',
        'api-key': api_key,
    }
    data = {
        "model": "aasare",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ]
    }
    async with session.post(f"{azure_endpoint}openai/deployments/aasare-35/chat/completions?api-version={api_version}", headers=headers, json=data) as response:
        if response.status == 200:
            response_json = await response.json()
            return response_json['choices'][0]['message']['content']
        else:
            print(f"Request failed with status code {response.status}: {await response.text()}")
            return None

def main():
    st.markdown(
        """
        <style>
        body {
            background-image: url('https://example.com/background.jpg');
            background-size: cover;
            background-repeat: no-repeat;
        }
        .blog-card {
            border: 1px solid #ccc;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: #f9f9f9;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            transition: box-shadow 0.3s;
        }
        .blog-card:hover {
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("Mental Health Companion")
    st.write("Hello! I am your mental health companion. How can I assist you today?")

    if "question" not in st.session_state:
        st.session_state.question = ""
    if "response" not in st.session_state:
        st.session_state.response = ""
    if "related_topic" not in st.session_state:
        st.session_state.related_topic = ""

    with st.form(key='question_form'):
        st.session_state.question = st.text_input(label="Enter your question")
        submit_button = st.form_submit_button(label='Submit')

    if submit_button and st.session_state.question:
        corrected_question = correct_spelling(st.session_state.question, topics)
        st.session_state.related_topic = get_related_topic(corrected_question, topics)
        if st.session_state.related_topic:
            st.session_state.response = asyncio.run(get_response_wrapper(corrected_question))
            if st.session_state.response:
                st.write("Response:", st.session_state.response)
                blog_links = blogs.get(st.session_state.related_topic.lower(), [])
                if blog_links:
                    st.write("### Related Blogs")
                    for blog_link in blog_links:
                        st.markdown(f'<a href="{blog_link}" target="_blank">Read Blog</a>', unsafe_allow_html=True)
        else:
            st.write("The question should be related to mental health topics.")

async def get_response_wrapper(question):
    async with aiohttp.ClientSession() as session:
        return await get_response(session, question)

if __name__ == "__main__":
    main()
