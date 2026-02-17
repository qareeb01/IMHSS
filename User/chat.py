# User/chat.py - Student Chat Handler
import re
import uuid
import datetime
from flask import jsonify, request, session
from .database import students, messages, flags
import anthropic
import os


# ============================================
# RISK DETECTION ENGINE  (v2 — fuzzy + regex)
# ============================================

class RiskDetector:
    """
    Regex-based risk detection.

    Why regex instead of plain `keyword in text`:
      - "kill my self"  → plain match misses the space;  \\s* catches it
      - "self-harm"     → plain match misses the hyphen; normalise() strips it
      - "hang mySelf"   → .lower() already handled this, but belt-and-braces
      - "suicidal"      → \\w* suffix catches all inflections of "suicid"
      - "wanna die"     → dedicated pattern covers common slang
      - "kms" / "unalive" → modern abbreviations added explicitly

    Each entry is (compiled_regex, canonical_label_for_dashboard).
    Patterns run against the *normalised* text (see _normalise()).
    """

    # ── Normalisation ───────────────────────────────────────────
    @staticmethod
    def _normalise(text: str) -> str:
        """
        Lower-case and strip noise that causes keyword misses:
          - hyphens / underscores / dots  →  space  (self-harm → self harm)
          - smart/curly apostrophes       →  '
          - non-alphanumeric except space →  removed
          - multiple spaces               →  single space
        """
        text = text.lower()
        text = re.sub(r'[-_./\\]', ' ', text)          # punctuation → space
        text = re.sub(r'[\u2018\u2019\u201c\u201d]', "'", text)  # curly quotes
        text = re.sub(r"[^\w\s']", ' ', text)          # remove remaining punct
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # ── HIGH RISK — immediate escalation ───────────────────────
    _HIGH = [
        # Self-directed harm — \w* after the verb stem catches all inflections:
        # kill / kills / killing  |  hang / hangs / hanging  etc.
        (re.compile(r'\bkill\w*\s*my\s*self\b'),        'kill myself'),
        (re.compile(r'\bhurt\w*\s*my\s*self\b'),        'hurt myself'),
        (re.compile(r'\bcut\w*\s*my\s*self\b'),         'cut myself'),
        (re.compile(r'\bhang\w*\s*my\s*self\b'),        'hang myself'),
        (re.compile(r'\bshoot\w*\s*my\s*self\b'),       'shoot myself'),
        (re.compile(r'\bstab\w*\s*my\s*self\b'),        'stab myself'),
        (re.compile(r'\bburn\w*\s*my\s*self\b'),        'burn myself'),
        (re.compile(r'\bslash\s+my\s+wrists?\b'),       'slash my wrists'),
        (re.compile(r'\bend\s+my\s+life\b'),            'end my life'),
        (re.compile(r'\btake\s+my\s+(own\s+)?life\b'),  'take my life'),
        (re.compile(r'\bend\s+it\s+all\b'),             'end it all'),

        # Wanting to die / not exist
        (re.compile(r'\bwant\s+to\s+die\b'),            'want to die'),
        (re.compile(r'\bwanna\s+die\b'),                'wanna die'),
        (re.compile(r'\bi\s+want\s+to\s+be\s+dead\b'), 'want to be dead'),
        (re.compile(r'\bbetter\s+off\s+dead\b'),        'better off dead'),
        (re.compile(r'\bno\s+reason\s+to\s+live\b'),    'no reason to live'),
        (re.compile(r"\bdon'?t\s+want\s+to\s+(be\s+)?alive\b"),
                                                        "don't want to be alive"),
        (re.compile(r'\bnot\s+worth\s+being\s+alive\b'),'not worth being alive'),
        (re.compile(r'\bwish\s+i\s+(was|were|am)\s+dead\b'), 'wish i was dead'),
        (re.compile(r'\bwish\s+i\s+never\s+(existed|was\s+born)\b'),
                                                        'wish i never existed'),

        # Overdose
        (re.compile(r'\bover\s*dos\w*\b'),              'overdose'),
        (re.compile(r'\btake\s+too\s+many\s+(pills?|tablets?|meds?)\b'),
                                                        'overdose on pills'),

        # Jump / fall
        (re.compile(r'\bjump\s+off\b'),                 'jump off'),
        (re.compile(r'\bthrow\s+my\s*self\s+off\b'),   'throw myself off'),

        # Suicide (all inflections)
        (re.compile(r'\bsuicid\w*\b'),                  'suicide'),

        # Modern slang / abbreviations
        (re.compile(r'\bkms\b'),                        'kms'),       # kill myself
        (re.compile(r'\bunalive\s*(my\s*self)?\b'),     'unalive'),   # TikTok euphemism
    ]

    # ── MEDIUM RISK — monitor closely ──────────────────────────
    _MEDIUM = [
        (re.compile(r'\bself\s*harm\w*\b'),             'self harm'),
        (re.compile(r'\bhate\s*my\s*self\b'),           'hate myself'),
        (re.compile(r'\bworthless\b'),                  'worthless'),
        (re.compile(r'\bhopeless\b'),                   'hopeless'),
        (re.compile(r"\bcan'?t\s+go\s+on\b"),          "can't go on"),
        (re.compile(r"\bgiv(e|ing)\s+up\b"),            'give up'),
        (re.compile(r'\bno\s+point\b'),                 'no point'),
        (re.compile(r'\brather\s+be\s+dead\b'),         'rather be dead'),
        (re.compile(r'\bdisappear\s+forever\b'),        'disappear forever'),
        (re.compile(r'\bnot\s+worth\s+living\b'),       'not worth living'),
        (re.compile(r'\bwish\s+i\s+wasn\'?t\s+here\b'), 'wish i wasn\'t here'),
        (re.compile(r"\beveryone\s+(would\s+be|is)\s+better\s+off\s+without\s+me\b"),
                'everyone better off without me'),
        (re.compile(r'\bnobody\s+(would\s+)?care\s+if\s+i\b'), 'nobody cares if i'),
        (re.compile(r'\bfeel\s+like\s+a\s+burden\b'),  'feel like a burden'),
        (re.compile(r'\bcan\'t\s+take\s+it\s+anymore\b'), "can't take it anymore"),
        (re.compile(r'\bno\s+way\s+out\b'),             'no way out'),
    ]

    # ── LOW RISK — general distress ────────────────────────────
    _LOW = [
        (re.compile(r'\bdepress\w*\b'),                 'depressed'),
        (re.compile(r'\banxi\w*\b'),                    'anxious'),
        (re.compile(r'\bstress\w*\b'),                  'stressed'),
        (re.compile(r'\boverwhelm\w*\b'),               'overwhelmed'),
        (re.compile(r"\bcan'?t\s+sleep\b"),             "can't sleep"),
        (re.compile(r'\binsomnia\b'),                   'insomnia'),
        (re.compile(r'\blon\w*(ly|liness)\b'),          'lonely'),
        (re.compile(r'\bsad(ness)?\b'),                 'sad'),
        (re.compile(r'\bcry\w*\b'),                     'crying'),
        (re.compile(r'\btired\s+of\s+life\b'),          'tired of life'),
        (re.compile(r'\bburnout\b'),                    'burnout'),
        (re.compile(r'\bpanic\w*\b'),                   'panic'),
        (re.compile(r'\bbreakdown\b'),                  'breakdown'),
        (re.compile(r'\bnumb\b'),                       'numb'),
        (re.compile(r'\bexhaust\w*\b'),                 'exhausted'),
    ]

    @staticmethod
    def detect(message_text: str):
        """
        Normalise then scan with regex patterns.

        Returns:
            tuple(risk_level: str, matched_keywords: list[str])
        """
        normalised = RiskDetector._normalise(message_text)

        # HIGH — stop at first tier with a match
        matched = [
            label for pattern, label in RiskDetector._HIGH
            if pattern.search(normalised)
        ]
        if matched:
            return ("high", matched)

        matched = [
            label for pattern, label in RiskDetector._MEDIUM
            if pattern.search(normalised)
        ]
        if matched:
            return ("medium", matched)

        matched = [
            label for pattern, label in RiskDetector._LOW
            if pattern.search(normalised)
        ]
        if matched:
            return ("low", matched)

        return ("none", [])


# ============================================
# AI RESPONSE HANDLER  (v2 — Mira persona)
# ============================================

class AIResponder:
    """
    Generates warm, varied, exercise-aware AI responses via Claude.

    Key changes from v1:
    - Named persona (Mira) with defined personality
    - Explicitly banned from repeating "I hear you"
    - Carries a built-in library of 6 exercises to suggest naturally
    - max_tokens raised to 500 (room for an exercise description)
    - Responds *to the specific topic* the student raised, not generically
    """

    SYSTEM_PROMPT = """You are Mira, a warm and genuinely caring mental health companion for university students. You feel like a knowledgeable older student or a good friend who takes wellbeing seriously  not a clinical bot reading from a script.

PERSONALITY:
- Engaged, warm, and real. You notice details in what the student says and respond to *them specifically*.
- Lightly conversational in tone — natural, not stiff.
- Genuinely encouraging without being fake or cheesy.
- Curious — you want to understand what's really going on.

VARY YOUR OPENING EVERY SINGLE RESPONSE. Rotate freely and never repeat the same opener in a conversation. Good openers include:
- Reflecting the specific thing they mentioned: "Exam season hitting hard  that's genuinely exhausting."
- Naming the emotion: "That kind of anxiety makes total sense given what you're dealing with."
- A direct, warm follow-up: "Tell me more — what's been the hardest part?"
- Gentle normalising: "A lot of students hit this exact wall around this time of year. You're not alone in it."
- Acknowledging the effort of speaking up: "It takes courage to actually say that out loud."

ABSOLUTELY BANNED — never use these phrases, not even once:
- "I hear you"
- "That sounds really heavy"
- "I'm here to listen"
- "You are not alone" (unless it's worked naturally into a specific sentence, not as a standalone)
- Any robotic, scripted opener that doesn't respond to what they specifically said

FOCUS ON WHAT THEY ACTUALLY SAID:
- If they mention exams → talk about the pressure of exams specifically.
- If they mention loneliness → talk about what it's like to feel disconnected on campus.
- If they mention a breakup → acknowledge the grief of that specifically.
- If they mention family pressure → reflect that back directly.
- Never give a response that could apply to any topic. Every response should only fit THIS student's message.

EXERCISES — suggest these naturally when the moment is right. Never force them. Describe them briefly and practically:

1. 🌬️ BOX BREATHING: "Breathe in for 4 counts, hold for 4, out for 4, hold for 4. Repeat 3 times. It switches your nervous system from panic to calm in under 2 minutes."

2. 🧠 5-4-3-2-1 GROUNDING: "Name 5 things you can see, 4 you can physically feel, 3 you can hear, 2 you can smell, 1 you can taste. It pulls your brain out of spiralling and into the present moment."

3. 🚶 MOVEMENT RESET: "Even a 5-minute walk outside can shift your body's stress chemistry. You don't need a workout — just move long enough to change your environment."

4. 📓 BRAIN DUMP + SORT: "Write everything that's weighing on you, then draw a line down the middle: left side is things you can act on, right side is things you can't control. This separates your real to-do list from unnecessary anxiety."

5. 💧 PHYSICAL RESET: "Splash cold water on your face, drink a full glass of water slowly, or hold an ice cube briefly. A physical sensation can interrupt a mental spiral fast."

6. 🌙 SLEEP/RACING MIND: "Before bed, write down everything you're worried about and physically close the notebook. Your brain keeps cycling through worries because it thinks it needs to hold them — writing them down tells it they're stored."

7. You can also direct them to the "Exercises" tab in the app for more ideas, but try to suggest one naturally in the flow of conversation when it fits.

RESPONSE LENGTH: 3-5 sentences. Enough to feel genuinely heard and to actually help  not so long it feels like a lecture or a list.

NEVER:
- Mention counselors, monitoring systems, escalation, or that anyone else may see this chat.
- Diagnose, prescribe, or claim clinical authority.
- Be dismissive ("don't worry, it'll be fine").
- Be fake-positive ("You've got this! 😊 Everything will work out!").
- Redirect away from the conversation unless the student asks.
- Repeat yourself across turns  vary your vocabulary, structure, and approach each time.

FOR CRISIS / SEVERE DISTRESS (suicidal thoughts, self-harm):
- Do not panic or become clinical.
- Acknowledge the pain directly, specifically, and without amplifying it.
- Tell them you're genuinely glad they said it out loud.
- Stay in the conversation  ask a grounding question to keep them present.
- Suggest the box breathing or 5-4-3-2-1 grounding as something to try right now, together.
- Make it clear this moment is not permanent and that pain this intense does shift.
- Never mention emergency numbers, hotlines, or that you are alerting anyone.

You are here to make students feel genuinely understood and a little less alone  and to give them something real and practical to try."""

    @staticmethod
    def get_response(student_message: str, conversation_history=None) -> str:
        """
        Build context-aware message list and call Claude.

        Args:
            student_message:      Current message from the student.
            conversation_history: List of recent message dicts from DB.

        Returns:
            AI response text (str).
        """
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            api_messages = []

            # Include last 6 turns for genuine conversational context
            if conversation_history:
                for msg in conversation_history:
                    api_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                    if msg.get("ai_response"):
                        api_messages.append({
                            "role": "assistant",
                            "content": msg["ai_response"]
                        })

            api_messages.append({"role": "user", "content": student_message})

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                system=AIResponder.SYSTEM_PROMPT,
                messages=api_messages
            )

            return response.content[0].text

        except Exception as e:
            print(f"AI API Error: {e}")
            # Fallback  varied so it doesn't feel like the same canned message
            fallbacks = [
                "Something glitched on my end  but I'm still here. "
                "What's been weighing on you most today?",
                "Quick hiccup on my side, sorry about that. "
                "Tell me what's going on — I want to hear it.",
                "Ran into a technical snag, but don't let that stop you. "
                "What did you want to share?"
            ]
            import random
            return random.choice(fallbacks)


# ============================================
# CHAT ROUTE HANDLER
# ============================================

def send_message():
    """
    POST /student/chat/send

    Request JSON:
        { "message": "...", "session_id": "<optional uuid>" }

    Response JSON:
        {
            "success": true,
            "ai_response": "...",
            "message_id": "<uuid>",
            "timestamp": "<ISO8601>"
        }
    """

    # ──  Validate session ─────────────────────────────────────
    if "student_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    student_id = session["student_id"]
    student_record = students.find_one({"_id": student_id})

    if not student_record:
        return jsonify({"error": "Student not found"}), 404

    counselor_id = student_record.get("counselor_id")

    # ──  Parse request ────────────────────────────────────────
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return jsonify({"error": "Message required"}), 400

    student_message = data["message"].strip()

    if not student_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(student_message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)"}), 400

    session_id = data.get("session_id") or str(uuid.uuid4())

    # ── 3. Risk detection (CRITICAL, do not skip) ──────────────
    risk_level, matched_keywords = RiskDetector.detect(student_message)
    flagged = risk_level in ("high", "medium")

    # ──  Recent conversation history (last 6 turns) ───────────
    conversation_history = list(
        messages.find(
            {"student_id": student_id, "session_id": session_id}
        ).sort("timestamp", -1).limit(6)
    )
    conversation_history.reverse()          # chronological order for the API

    # ──  Get AI response ──────────────────────────────────────
    ai_response = AIResponder.get_response(student_message, conversation_history)

    # ──  Persist message ──────────────────────────────────────
    message_id = str(uuid.uuid4())
    timestamp  = datetime.datetime.utcnow()

    message_doc = {
        "_id":          message_id,
        "student_id":   student_id,
        "counselor_id": counselor_id,
        "session_id":   session_id,
        "content":      student_message,
        "ai_response":  ai_response,
        "risk_level":   risk_level,
        "flagged":      flagged,
        "timestamp":    timestamp,
    }
    messages.insert_one(message_doc)

    # ──  Create risk flag if needed ───────────────────────────
    if flagged:
        flag_doc = {
            "_id":               str(uuid.uuid4()),
            "message_id":        message_id,
            "student_id":        student_id,
            "counselor_id":      counselor_id,
            "risk_level":        risk_level,
            "detected_keywords": matched_keywords,
            "flagged_at":        timestamp,
            "reviewed":          False,
            "reviewed_at":       None,
            "reviewed_by":       None,
            "notes":             None,
        }
        flags.insert_one(flag_doc)

        print(f"[{risk_level.upper()} RISK FLAG] "
              f"student={student_id}  keywords={matched_keywords}")

    # ── Return response, never mention the flag ─────────────
    return jsonify({
        "success":    True,
        "ai_response": ai_response,
        "message_id": message_id,
        "timestamp":  timestamp.isoformat(),
    }), 200
