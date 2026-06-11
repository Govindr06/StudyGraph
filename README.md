
# StudyGraph: Autonomous Learning Planner 🧠📅

## Flask Migration Instructions

This project now uses Flask for login, static file serving, and backend APIs. The Streamlit UI is replaced by a custom HTML/JS interface in `index.html`.

### How to Run (Flask Version)
1. Install dependencies:
   ```sh
   pip install flask
   ```
2. Start the Flask app:
   ```sh
   python flask_app.py
   ```
3. Open your browser and go to [http://localhost:5000](http://localhost:5000)

Place any JS, CSS, or image files in the `static/` directory and reference them as `/static/filename.ext` in your HTML.


StudyGraph is an AI-powered, autonomous learning scheduler built with Python and Streamlit. It takes a user's study goal, uses a LangGraph agent powered by Groq's Llama 3.3 to generate a comprehensive multi-day syllabus, and automatically schedules full ~500-word daily lessons directly into the user's Google Calendar.

## ✨ Features
* **Seamless Google OAuth Integration:** One-click login and automatic URL redirect handling for Google Calendar permissions.
* **AI Agentic Workflow:** Utilizes LangGraph to intelligently break down complex study goals into structured, sequential modules.
* **Content Generation:** Automatically writes full, detailed daily lessons (including concepts, examples, exercises, and recaps) using Groq's ultra-fast LLM API.
* **Persistent Storage:** Saves user profiles and generated study schedules securely to a PostgreSQL database.
* **Calendar Sync:** Pushes the generated curriculum to Google Calendar, embedding the AI-generated lessons directly into the event descriptions.
* **Rate-Limit Resilient:** Built-in exponential backoff and pacing logic to handle API speed limits smoothly.

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **Backend:** Python 3.11+
* **AI/Agent Framework:** LangGraph, LangChain
* **LLM Provider:** Groq (llama-3.3-70b-versatile)
* **Database:** PostgreSQL (with `psycopg2`)
* **Integrations:** Google Calendar API, Google OAuth 2.0

## 🚀 Getting Started

### Prerequisites
1. Python 3.11 or higher installed.
2. PostgreSQL installed and running locally.
3. A Google Cloud Console project with the Calendar API enabled and OAuth 2.0 credentials generated.
4. A free Groq API key.

### Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/V-33/StudyGraph.git](https://github.com/V-33/StudyGraph.git)
   cd StudyGraph

2. **Create and activate a virtual environment:**

Bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
3. **Install the dependencies:**

Bash
pip install -r requirements.txt
4. **Environment Variables:**
Create a .env file in the root directory and add the following keys:

Code snippet
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8501

# Groq AI Key
GROQ_API_KEY=your_groq_key_here

# PostgreSQL Database URL
DATABASE_URL=postgresql://username:password@localhost:5432/studygraph_db
5. **Run the Application:**

Bash
python -m streamlit run app.py

🎯 Usage
Open http://localhost:8501 in your browser.

Click Login with Google to authorize Calendar access.

Enter a study goal (e.g., "Teach me Oracle SQL in 14 days").

Click Generate, Schedule, and Save.

Once the table populates, click Push Unsynced Events to send the lessons to your Google Calendar!