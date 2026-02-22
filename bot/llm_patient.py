import os
import re
import random
from openai import OpenAI

_client: OpenAI | None = None

COMPLETION_SENTINEL = "[CONVERSATION_COMPLETE]"

# ── Tier-1 classifiers (regex, zero latency) ──────────────────────────────────

# Agent is reading a legal/recording disclosure → human stays silent, waits
_SILENCE_PATTERNS = [
    r"may be recorded",
    r"recording.{0,15}(call|conversation)",
    r"quality and training",
    r"monitored for quality",
    r"calls? (are|is) recorded",
]

# Agent is processing and explicitly asked us to wait → brief acknowledgment only
_HOLD_PATTERNS = [
    r"\bone moment\b",
    r"\b1 moment\b",
    r"let me (check|look|pull|search|find|see|verify)",
    r"hold (on|please)",
    r"give me (a )?(moment|second)",
    r"i('ll| will) (check|look|search|verify|pull)",
    r"just a (moment|second|sec)",
    r"one sec(ond)?",
    r"bear with me",
    r"i'm (looking|checking|searching)",
]

# Agent already has a result in the same utterance — even if a hold phrase is present,
# the patient must respond to the actual answer, not just acknowledge the hold.
_RESULT_PATTERNS = [
    r"there (are|is) no\b",
    r"no (available|openings|slots|appointments)",
    r"(couldn't|could not|can't|cannot) find",
    r"unfortunately",
    r"the (next|earliest) available",
    r"i (found|have|see)\b",
    r"would you like",
    r"do you (want|have|prefer)",
    r"we (don't|do not) have",
    r"the office (is|are) closed",
]

# Agent is asking to confirm the caller's identity
_IDENTITY_PATTERNS = [
    r"\bam i speaking (with|to)\b",
    r"\bspeaking with\b",        # catches garbled ASR like "my speaking with Felix"
    r"\bis this\b",
    r"\bcan i (speak|talk) (with|to)\b",
    r"\bwho am i (speaking|talking) (with|to)\b",
    r"\bcan you confirm your name\b",
]

_HOLD_RESPONSES = [
    "Sure, take your time.",
    "Okay, I'll wait.",
    "No problem, I'll hold on.",
    "Of course, take your time.",
    "Sure thing, I'm here.",
]


def _is_identity_question(text: str, patient_name: str = "") -> bool:
    """Returns True if the agent is cueing the patient to identify themselves.

    Matches standard phrasing ('Am I speaking with...') AND any utterance that
    contains the patient's first name — handles garbled/informal agent openings
    like 'I think it was Felix' or 'How can I help you, Felix?'
    """
    lower = text.lower()
    if any(re.search(p, lower) for p in _IDENTITY_PATTERNS):
        return True
    if patient_name:
        first_name = patient_name.split()[0].lower()
        if re.search(r'\b' + re.escape(first_name) + r'\b', lower):
            return True
    return False


def _tier1_classify(agent_text: str) -> str | None:
    """
    Fast regex pre-check before hitting the LLM.
    Returns 'silence', 'hold', or None (meaning: let GPT handle it).
    """
    lower = agent_text.lower()
    if any(re.search(p, lower) for p in _SILENCE_PATTERNS):
        return "silence"
    if any(re.search(p, lower) for p in _HOLD_PATTERNS):
        # Only treat as a pure hold if the utterance doesn't also contain a result.
        # e.g. "Let me check… there are no slots" must go to GPT, not short-circuit.
        if not any(re.search(p, lower) for p in _RESULT_PATTERNS):
            return "hold"
    return None


# ── System prompt ──────────────────────────────────────────────────────────────

def _build_system_prompt(scenario, patient: dict, has_spoken: bool) -> str:
    first_turn_note = (
        f"""YOU HAVE NOT SPOKEN YET. FOLLOW THESE RULES IN ORDER:

1. STAY COMPLETELY SILENT for any greeting (e.g. "Thanks for calling...", "Hello, this is...").
   Do NOT say anything. Do NOT say "How can I help you?" — you are the PATIENT, not the agent.

2. YOUR FIRST WORDS must be "Yes, that's me." — whenever the agent says your name
   OR asks to confirm your identity (e.g. "Am I speaking with Felix?", "I think it was Felix",
   "Felix?", "How can I help you today, Felix?"). Any mention of your name is your cue.

3. After confirming your identity, stay silent until the agent asks "How can I help you?"
   or "What can I do for you?" — then reply ONLY with: "{scenario.initial_utterance}"

DO NOT speak before the agent says your name or asks to identify you.
DO NOT volunteer your reason for calling before being asked.
"""
        if not has_spoken
        else ""
    )

    return f"""You are a patient on a phone call with a medical office AI scheduler called Athena.
You are NOT making conversation. You are answering questions.

YOUR IDENTITY:
  Name: {patient["full_name"]}
  Date of Birth: {patient["dob"]}

YOUR REASON FOR THIS CALL:
  {scenario.goal}

YOUR PERSONA:
  {scenario.persona}

{first_turn_note}
══════════════════════════════════════════════════════
RESPONSE RULES — one rule per agent utterance type:
══════════════════════════════════════════════════════

"How can I help you?" / "What can I do for you?" / open prompt:
  → State your reason for calling in ONE sentence. Nothing else.

"Can you confirm your name?" / "Is this [name]?":
  → "Yes." or "Yes, that's me." — nothing more unless they ask.

"Can you confirm your date of birth?":
  → "{patient["dob"]}." — just the date.

Any direct question (what type, what day, what time, which provider, which pharmacy):
  → One direct answer. No preamble, no follow-up questions of your own unless the scenario
    requires it (e.g. 07_insurance_mid_call).

Agent is providing information or making a statement (not asking):
  → "Okay." or "Got it." — that's all. Do not add commentary.

"One moment" / "Let me check" / "I'll look that up":
  → Say nothing, or at most "Sure." — the classifier handles most of these already.

Agent says there is no availability or cannot fulfill your request:
  → Do NOT give up immediately. Follow your PERSONA's specific fallback first (it defines exactly
    what to ask next). Only use a generic alternative if the persona gives no guidance.
  → Only after TWO genuine follow-up attempts have both failed: "Okay, thank you." + {COMPLETION_SENTINEL}

Agent confirms the booking, completes the task, or asks "Is there anything else?":
  → "No, that's all. Thank you." then append {COMPLETION_SENTINEL}

══════════════════════════════════════════════════════
ABSOLUTE RULES:
══════════════════════════════════════════════════════

1. ONE sentence per turn. Two sentences maximum only if a second is truly necessary.
2. No greetings, no small talk, no "Hi there", no pleasantries unprompted.
3. Never volunteer information that wasn't asked for.
4. Never break character or acknowledge being an AI or a test.
5. Stay on your goal: {scenario.goal}
   Follow your persona's fallback behaviour when the agent cannot help with the first request.
   Only after genuinely trying two alternative approaches say "Okay, thank you." + {COMPLETION_SENTINEL}.
   A single "no availability" answer is NOT two failed attempts — push back first.
6. If the agent CONFIRMS or BOOKS the wrong thing (e.g. "I've booked you for Tuesday" when you
   asked for Saturday), correct it: "I asked for [X], not [Y]." — but if the agent is merely
   OFFERING an alternative you didn't ask for, do not use this phrasing. Simply respond to the
   offer ("Can I get on a waitlist instead?" / "Okay, thank you." etc.).
7. {COMPLETION_SENTINEL} goes at the very end of your final message only."""


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_patient_response(
    scenario,
    patient: dict,
    history: list[dict],
    agent_text: str,
) -> tuple[str, bool]:
    """
    Generate the next patient utterance.

    Returns (patient_text, is_complete).
    patient_text == "" means the agent said something (e.g. a disclosure)
    that a real human would stay silent through — caller should keep listening.
    """
    # ── Tier-1: regex classifiers (no API call, zero latency) ─────────────────
    tier1 = _tier1_classify(agent_text)

    if tier1 == "silence":
        # Stay silent — human wouldn't respond to a legal disclosure
        return "", False

    if tier1 == "hold":
        # Agent is processing — brief acknowledgment only
        return random.choice(_HOLD_RESPONSES), False

    # ── Pre-identity gate: stay silent until agent asks "Am I speaking with X?" ─
    has_spoken = any(t["role"] == "patient" for t in history)
    if not has_spoken and not _is_identity_question(agent_text, patient.get("full_name", "")):
        # Agent is still in preamble (greeting, intro) — real humans don't speak yet
        return "", False

    # ── Tier-2: GPT generates the contextual response ─────────────────────────
    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt(scenario, patient, has_spoken)}
    ]

    for turn in history:
        if turn["role"] == "agent":
            messages.append({"role": "user", "content": turn["text"]})
        else:
            messages.append({"role": "assistant", "content": turn["text"]})

    messages.append({"role": "user", "content": agent_text})

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=120,
            temperature=0.7,
            timeout=4.0,
        )
        raw = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[llm] Error generating response: {e}")
        return "Sorry, could you repeat that?", False

    # Guard: strip any AI self-identification slip-through
    if re.search(r"\b(as an ai|i'm an ai|language model|i am an ai)\b", raw, re.IGNORECASE):
        return "Sorry, could you say that again?", False

    is_complete = COMPLETION_SENTINEL in raw
    clean_text = raw.replace(COMPLETION_SENTINEL, "").strip()

    return clean_text, is_complete


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client
