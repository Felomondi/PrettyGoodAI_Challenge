# Pretty Good AI — Engineering Challenge

## Overview

Build a voice bot that calls our test line and has conversations with our AI agent.
Your bot will act as a "patient" testing our system—finding bugs, evaluating quality,
and stress-testing edge cases.

This challenge tests what we actually care about: can you build something that works,
reason through ambiguous problems, and ship?

## Before You Start

**Cost note:** Depending on which APIs and LLMs you use, there will be usage fees.
Successful submissions typically cost less than $20 total in API and telephony charges.

## Setup

Create a test account at pgai.us/athena — this gives you context on how our product
works and what patients experience. **Do not call the number shown on the confirmation screen.**

**All test calls must go to: +1-805-439-8008** — this is the number for this assessment.

## The Task

Build an automated voice bot that:

1. Calls only our test number: +1-805-439-8008
2. Simulates realistic patient scenarios (scheduling, refills, questions, etc.)
3. Records and transcribes the conversations
4. Identifies bugs or quality issues in our agent's responses

## Requirements

### Deliverables (all in GitHub)

- **Working code** — Your voice bot, written in Python
- **README** — Clear setup and run instructions (ideally a single command after setup)
- **Architecture doc** — 1–2 paragraphs explaining how your system works and why you made key design choices
- **Call transcripts** — Minimum 10 calls with both sides of each conversation. A good call is a full conversation (typically 1–3 minutes) — not a single question and hang-up
- **Bug report** — Document issues you found (see example below)
- **Loom video** — Walkthrough of your approach and what you built (max 5 minutes, free Loom account). This is one of the most important deliverables — show us how you think

### Example Bug Report Entry

> **Bug:** Agent confirms appointment for Sunday but the practice is closed on weekends
> **Severity:** High
> **Call:** transcript-07.txt at 1:23
> **Details:** When asked "Can I come in Sunday at 10am?", the agent responded "I've scheduled you for Sunday at 10am" without checking office hours. Should have informed the patient the office is closed on weekends and offered the next available weekday.

You don't need to follow this exact format — just be clear about what happened, why it's a problem, and where to find it.

### Code Standards

- Clean, readable code with reasonable structure
- Document any API keys or environment variables needed (do not commit secrets)
- Include a `.env.example` file showing required variables

## Call Scenarios to Test

Cover a variety of scenarios, such as:

- Simple appointment scheduling
- Rescheduling or canceling
- Medication refill requests
- Questions about office hours, locations, insurance
- Edge cases — interruptions, unclear requests, unusual scenarios

You're testing our AI. Be creative about finding its limits.

## Time Expectations

- **Expected time:** 6–12 hours
- **Minimum submission:** 10 calls — no exceptions. Quality matters, so make them count
- **Go further:** Diverse scenarios, deeper analysis, and creative edge cases — this is how you stand out

## Submission Instructions

1. Create a public GitHub repository with your solution
2. Email your submission to: kevin@prettygoodai.com
3. Your email must include:
   - GitHub repository link
   - Loom walkthrough link
   - The one phone number you used to call our bot during testing, in E.164 format (example: +13334445555)
4. Your email subject line must follow this exact format:

```
Subject: PGA I BUILT IT: <Your Full Name> <Your Bot Phone Number>
```

Example: `PGA I BUILT IT: Jane Smith +13334445555`

There is no hard deadline. Submissions are reviewed on a first-in, first-reviewed basis.

## Evaluation Criteria

### First step
We listen to the voice calls your bot made.

### What we're looking for (in priority order)

1. **Quality of bugs found** — Useful, well-described issues beat a long list of nitpicks
2. **Working code that makes real calls** — It has to actually work
3. **Clear thinking** — Architecture doc and Loom show how you reason
4. **Evidence you iterated** — Did you improve your bot after hearing early results?
5. **Clean enough code to read** — Not perfect, just understandable

### What we're NOT looking for

- Perfect code or over-engineering
- Fancy diagrams
- Nitpicks about punctuation
- One-shot copy-paste from AI
- Production-grade infrastructure
