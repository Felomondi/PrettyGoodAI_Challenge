# PrettyGoodAI Voice Bot

Automated voice bot that calls the Athena test line (`+1-805-439-8008`), simulates patient conversations, and generates a bug report.

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Add your API keys**
```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `TWILIO_ACCOUNT_SID` | [console.twilio.com](https://console.twilio.com) → Account Info |
| `TWILIO_AUTH_TOKEN` | Same page |
| `TWILIO_FROM_NUMBER` | Twilio Console → Phone Numbers |
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `NGROK_AUTH_TOKEN` | [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken) |

`PATIENT_FULL_NAME` and `PATIENT_DOB` are pre-filled in `.env.example` — leave them as-is.

## Run

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000) and use the UI to run individual scenarios or all at once.

Transcripts → `transcripts/` · Bug report → `outputs/bug_report.md`
