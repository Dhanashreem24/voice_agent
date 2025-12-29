# ADK Voice Agent

This project enables a voice-based interface for your existing Google ADK (Agent Development Kit) Agent, leveraging Twilio for telephony and a local FastAPI server for processing.

The system allows users to call a phone number and interact with the `RootDispatcher` and its sub-agents (`BillingAgent`, `TechSupportAgent`) using natural language.

---

## 🏗️ Architecture

![Architecture Diagram](image.png)

**Key Improvements:**
*   **Latency Masking**: Immediate feedback ("Please bear with me...") prevents dead air while the LLM thinks.
*   **Session Management**: Maintains conversation history for the duration of the call.
*   **Automatic Tool Execution**: Uses the ADK `Runner` to handle tool calls seamlessly.

---

## 🚀 Setup & Installation

### 1. Prerequisites
*   **Python 3.10+** (in `adk-env` conda environment)
*   **Twilio Account** (with an active phone number)
*   **ngrok** (for exposing local server to Twilio)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Ensure `pyaudio` and `pyttsx3` are installed for local testing)*

### 3. Run the Server
Start the FastAPI server which handles the Twilio webhooks:
```bash
conda run -n adk-env uvicorn server:app --port 8000 --reload
```

---

## 🧪 Testing

### Option A: Local Text Tester (Recommended for Logic)
Test the agent logic without speaking:
```bash
conda run -n adk-env python text_to_speech_tester.py
```
*   **Input**: Type "Check my balance"
*   **Output**: Agent responds via text (and TTS)

### Option B: Local Voice Tester (Virtual Twilio)
Simulate the full voice loop using your microphone:
```bash
conda run -n adk-env python local_tester.py
```

### Option C: Real Phone Call (Production)
1.  **Expose Server**:
    ```bash
    ngrok http 8000
    ```
2.  **Configure Twilio**:
    *   Go to **Twilio Console > Phone Numbers > Manage > Active Numbers**.
    *   Select your number -> **Voice & Fax**.
    *   Set **"A CALL COMES IN"** to **Webhook**.
    *   URL: `https://<your-ngrok-id>.ngrok-free.app/voice`
    *   Method: **POST**
    *   Save.
3.  **Call**: Dial the number and speak!

---

## 📂 Project Structure

*   `server.py`: Main application handling `/voice` (Greeting), `/gather_speech` (Input), and `/process_speech` (Agent Execution).
*   `local_tester.py`: Script to simulate Twilio locally using Microphone/Speakers.
*   `text_to_speech_tester.py`: Script to test the agent via text input.
*   `agents/root_agent.py`: The entry point for the ADK Agent.
*   `prompts/system_prompts.py`: System instructions for the agents.

---

## 🛠️ Troubleshooting

*   **"Session not found"**: Ensure `USER_SESSION_MAP` logic in `server.py` is active.
*   **Twilio 500 Error**: Check `server.log` or the terminal output for crashes.
*   **Latency**: The "Please bear with me" message is designed to cover the 2-5s delay of the LLM.
