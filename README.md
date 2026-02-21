# PrettyGoodAI Voice Bot

An automated voice bot that calls the PrettyGoodAI Athena test line, simulates realistic
patient conversations, records transcripts, and generates a bug report identifying issues
in the agent's responses.

## Prerequisites

- Python 3.11+
- [Twilio](https://twilio.com) account with one provisioned phone number
- [OpenAI](https://platform.openai.com) API key (fund with ~$5)
- [Supabase](https://supabase.com) project (free tier)
- [ngrok](https://ngrok.com) account (free tier, for the public webhook URL)
- Node.js 18+ _(only needed if you edit the TypeScript source in `frontend/`)_

## Setup

### 1. Clone and install Python dependencies

```bash
git clone <your-repo-url>
cd PrettyGoodAI_Challenge

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Open .env and fill in all values
```

| Variable | Where to find it |
|---|---|
| `TWILIO_ACCOUNT_SID` | [Twilio Console](https://console.twilio.com) → Account Info |
| `TWILIO_AUTH_TOKEN` | Same page |
| `TWILIO_FROM_NUMBER` | Twilio Console → Phone Numbers |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `NGROK_AUTH_TOKEN` | [ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken) |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase → Project Settings → API → `anon public` key |

### 3. Create the Supabase table

In your Supabase project go to **SQL Editor** and run:

```sql
CREATE TABLE patients (
    id         BIGSERIAL PRIMARY KEY,
    full_name  TEXT      NOT NULL,
    email      TEXT      NOT NULL UNIQUE,
    phone      TEXT      NOT NULL UNIQUE,
    dob        TEXT      NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Register a test patient

```bash
python run.py --setup
```

Visit [http://localhost:5000/register](http://localhost:5000/register) and register a patient.

> **Important:** Register the **exact same patient** (same phone number, name, and date of birth)
> at [pgai.us/athena](https://pgai.us/athena). The Athena agent identifies callers by phone
> number and greets them by name — this is how the bot knows what identity to use.

## Run

```bash
python run.py
```

This will:

1. Start an ngrok tunnel and update the Twilio webhook URL automatically
2. Start the Flask server in a background thread
3. Place 15 test calls to `+1-805-439-8008`, spaced 90 seconds apart
4. Save conversation transcripts to `transcripts/`
5. Run GPT-4o-mini bug analysis across all transcripts
6. Write `outputs/bug_report.md`

## Output

| Path | Contents |
|---|---|
| `transcripts/*.txt` | Human-readable conversation transcripts |
| `transcripts/*.json` | Machine-readable transcripts (used for analysis) |
| `outputs/bug_report.md` | Bug report sorted by severity |
| `outputs/transcripts/` | Formatted transcripts for repo submission |

## Editing TypeScript

The frontend uses TypeScript compiled to `static/js/form.js`. The compiled file is committed
so you don't need Node.js to run the app. If you modify `frontend/form.ts`:

```bash
cd frontend
npm install
npm run build   # compiles to ../static/js/form.js
```

## Architecture

See `PLAN.md` for the full architecture and technical decisions.

**In brief:** The bot uses Twilio to place outbound calls. When a call connects, Flask
serves TwiML that makes the bot speak (via Amazon Polly) and listen. Each agent reply is
transcribed by Twilio's built-in STT and sent to a webhook. GPT-4o-mini generates the
patient's next utterance using the registered patient's real name and date of birth, so
the agent's identity verification flow works correctly. After all calls complete, another
GPT-4o-mini pass analyzes the transcripts for bugs.
