# User/chat.py - Student Chat Handler with Clinical Risk Detection
import re
import uuid
import datetime
from flask import jsonify, request, session
from .database import students, messages, flags
import anthropic
import os


# ============================================
# WEIGHTED RISK DETECTION ENGINE
# Clinical-grade with context awareness
# ============================================

class RiskDetector:
    """
    Intelligent risk detection using weighted scoring.

    Scoring System:
    - 0-3 points   = Low Risk (general distress)
    - 4-7 points   = Medium Risk (serious concern)
    - 8-11 points  = High Risk (urgent intervention)
    - 12+ points   = Red Code (immediate crisis)
    Each pattern has a weight based on clinical severity. Multiple patterns can accumulate to increase risk level, allowing for nuanced detection of complex messages. Context filters help reduce false positives on common phrases that may sound alarming but are not (e.g., "dying of laughter").

    Multiple keywords compound severity.
    """

    @staticmethod
    def _normalise(text: str) -> str:
        """Normalize text for accurate pattern matching"""
        text = text.lower()
        text = re.sub(r'[-_./\\]', ' ', text)
        text = re.sub(r'[\u2018\u2019\u201c\u201d]', "'", text)
        text = re.sub(r"[^\w\s']", ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # ════════════════════════════════════════════════════════════════
    # CRITICAL PATTERNS (Weight: 8 each - immediate high risk)
    # ════════════════════════════════════════════════════════════════
    _CRITICAL = [
        # Suicidal ideation
        (re.compile(r'\b(want to|wanna|going to|plan to|trying to)\s+die\b'), 'want to die', 8),
        (re.compile(r'\b(kill|hurt|cut|hang|shoot|stab|burn)\w*\s+(my\s*)?self\b'), 'self-harm intent', 8),
        (re.compile(r'\b(end|take)\s+my\s+(own\s+)?life\b'), 'end my life', 8),
        (re.compile(r'\bsuicid(e|al|ing)\b'), 'suicide', 8),
        (re.compile(r'\b(kms|unalive)\b'), 'kms/unalive', 8),
        (re.compile(r'\bwish\s+i\s+(was|were)\s+dead\b'), 'wish i was dead', 8),
        (re.compile(r'\bbetter\s+off\s+dead\b'), 'better off dead', 8),
        
        # Active self-harm
        (re.compile(r'\bi\s+(cut|burned|hit)\s+(my\s*)?self\b'), 'i cut/burned myself', 8),
        (re.compile(r'\bi\s+want\s+to\s+cut\b'), 'want to cut', 8),
        (re.compile(r'\bburning\s+myself\s+helps\b'), 'burning myself', 8),
        (re.compile(r'\bi\s+deserve\s+pain\b'), 'deserve pain', 8),
        (re.compile(r'\bi\s+need\s+to\s+hurt\s+myself\b'), 'need to hurt myself', 8),
        (re.compile(r'\b(like|love)\s+seeing\s+myself\s+bleed\b'), 'like seeing myself bleed', 8),
        (re.compile(r'\bslash\w*\s+my\s+wrist\b'), 'slash my wrists', 8),
        
        # Psychosis
        (re.compile(r'\bi\s+hear\s+voices\b'), 'hear voices', 8),
        (re.compile(r'\bvoices?\s+(are\s+)?(telling|tell|told)\s+me\b'), 'voices telling me', 8),
        (re.compile(r'\bsomeone\s+is\s+watching\s+me\b'), 'someone watching me', 8),
        (re.compile(r'\b(they\'re|people\s+are)\s+following\s+me\b'), 'being followed', 8),
        (re.compile(r'\bi\s+see\s+things\s+others\s+don\'?t\b'), 'seeing things', 8),
        (re.compile(r'\b(tv|computer|phone)\s+is\s+sending\s+me\s+messages\b'), 'delusional thoughts', 8),
        (re.compile(r'\bpeople\s+are\s+plotting\s+against\s+me\b'), 'paranoia', 8),
        (re.compile(r'\bi\'?m\s+not\s+real\b'), 'i\'m not real', 8),
        (re.compile(r'\bnothing\s+feels\s+real\b'), 'nothing feels real', 8),
        
        # Overdose/poisoning
        (re.compile(r'\bover\s*dos(e|ed|ing)\b'), 'overdose', 8),
        (re.compile(r'\b(take|took)\s+(too\s+many|all\s+my)\s+(pills?|tablets?|meds?)\b'), 'took too many pills', 8),
        
        # Ongoing abuse/danger
        (re.compile(r'\bmy\s+(partner|boyfriend|girlfriend|husband|wife|dad|mom)\s+hits\s+me\b'), 'partner/parent hits me', 8),
        (re.compile(r'\bi\'?m\s+scared\s+of\s+(him|her|them)\b'), 'scared of abuser', 8),
        (re.compile(r'\bthey\s+threaten\s+me\b'), 'being threatened', 8),
        (re.compile(r'\bi\'?m\s+not\s+allowed\s+to\s+leave\b'), 'not allowed to leave', 8),
        (re.compile(r'\bi\'?m\s+trapped\b'), 'i\'m trapped', 8),
        (re.compile(r'\bdon\'?t\s+feel\s+safe\s+at\s+home\b'), 'don\'t feel safe at home', 8),
    ]

    # ════════════════════════════════════════════════════════════════
    # SEVERE PATTERNS (Weight: 5 each - serious concern)
    # ════════════════════════════════════════════════════════════════
    _SEVERE = [
        # Severe hopelessness
        (re.compile(r'\b(there\'?s\s+)?no\s+point\s+(in\s+)?(living|going\s+on)\b'), 'no point living', 5),
        (re.compile(r'\bi\'?m\s+done\b'), 'i\'m done', 5),
        (re.compile(r'\bi\s+give\s+up\b'), 'give up', 5),
        (re.compile(r'\bnothing\s+matters\s+anymore\b'), 'nothing matters', 5),
        (re.compile(r'\bdon\'?t\s+see\s+a\s+future\b'), 'don\'t see a future', 5),
        (re.compile(r'\bdon\'?t\s+belong\s+anywhere\b'), 'don\'t belong', 5),
        (re.compile(r'\beveryone\s+(would\s+be|is)\s+better\s+(off\s+)?without\s+me\b'), 'better without me', 5),
        (re.compile(r'\bi\'?m\s+a\s+burden\b'), 'i\'m a burden', 5),
        (re.compile(r'\bworthless\b'), 'worthless', 5),
        (re.compile(r'\bhopeless\b'), 'hopeless', 5),
        (re.compile(r'\bno\s+way\s+out\b'), 'no way out', 5),
        (re.compile(r'\bcan\'?t\s+go\s+on\b'), 'can\'t go on', 5),
        (re.compile(r'\bcan\'?t\s+take\s+it\s+anymore\b'), 'can\'t take it anymore', 5),
        (re.compile(r'\bi\'?m\s+tired\s+of\s+everything\b'), 'tired of everything', 5),
        
        # Severe anxiety/panic
        (re.compile(r'\bi\s+can\'?t\s+breathe\b'), 'can\'t breathe', 5),
        (re.compile(r'\bmy\s+chest\s+is\s+tight\b'), 'chest is tight', 5),
        (re.compile(r'\bi\s+feel\s+like\s+i\'?m\s+dying\b'), 'feel like dying', 5),
        (re.compile(r'\b(my\s+)?heart\s+is\s+racing\b'), 'heart racing', 5),
        (re.compile(r'\blos(e|ing)\s+control\b'), 'losing control', 5),
        (re.compile(r'\b(i\'?m\s+)?(going|gone)\s+crazy\b'), 'going crazy', 5),
        (re.compile(r'\bcan\'?t\s+calm\s+down\b'), 'can\'t calm down', 5),
        (re.compile(r'\bterrified\s+for\s+no\s+reason\b'), 'terrified for no reason', 5),
        (re.compile(r'\bpanic\s+attack\s+again\b'), 'panic attack again', 5),
        
        # PTSD/trauma
        (re.compile(r'\bflashback\w*\b'), 'flashbacks', 5),
        (re.compile(r'\bit\s+keeps\s+replaying\s+in\s+my\s+head\b'), 'replaying in my head', 5),
        (re.compile(r'\bcan\'?t\s+sleep\s+because\s+of\s+what\s+happened\b'), 'can\'t sleep trauma', 5),
        (re.compile(r'\bnightmares?\s+every\s+night\b'), 'nightmares every night', 5),
        (re.compile(r'\bi\s+feel\s+unsafe\b'), 'feel unsafe', 5),
        (re.compile(r'\bi\'?m\s+scared\s+all\s+the\s+time\b'), 'scared all the time', 5),
        (re.compile(r'\bi\s+was\s+assault(ed)?\b'), 'was assaulted', 5),
        (re.compile(r'\bi\s+was\s+abus(ed)?\b'), 'was abused', 5),
        (re.compile(r'\bi\s+freeze\s+when\s+i\s+remember\b'), 'freeze when i remember', 5),
        (re.compile(r'\bptsd\b'), 'PTSD', 5),
        
        # Eating disorders (severe)
        (re.compile(r'\bhaven\'?t\s+eaten\s+in\s+days\b'), 'haven\'t eaten in days', 5),
        (re.compile(r'\bi\s+threw\s+up\s+after\s+eating\b'), 'threw up after eating', 5),
        (re.compile(r'\bi\s+feel\s+fat\s+and\s+disgusting\b'), 'feel fat and disgusting', 5),
        (re.compile(r'\bstarv(e|ed|ing)\s+myself\b'), 'starving myself', 5),
        (re.compile(r'\bi\s+need\s+to\s+purge\b'), 'need to purge', 5),
        (re.compile(r'\bi\'?m\s+scared\s+of\s+food\b'), 'scared of food', 5),
        (re.compile(r'\bi\s+binge\s+and\s+(then\s+)?vomit\b'), 'binge and vomit', 5),
        (re.compile(r'\bi\s+only\s+ate\s+once\s+this\s+week\b'), 'ate once this week', 5),
        
        # Addiction/substance abuse
        (re.compile(r'\bcan\'?t\s+stop\s+drinking\b'), 'can\'t stop drinking', 5),
        (re.compile(r'\bi\s+drink\s+every\s+day\b'), 'drink every day', 5),
        (re.compile(r'\bi\s+need\s+drugs\s+to\s+function\b'), 'need drugs to function', 5),
        (re.compile(r'\bi\s+black\s+out\s+often\b'), 'black out often', 5),
        (re.compile(r'\bi\s+use\s+to\s+forget\b'), 'use to forget', 5),
        (re.compile(r'\bcan\'?t\s+go\s+a\s+day\s+without\s+it\b'), 'can\'t go a day without it', 5),
        (re.compile(r'\bi\s+need\s+stronger\s+stuff\b'), 'need stronger stuff', 5),
        (re.compile(r'\bi\s+take\s+more\s+than\s+prescribed\b'), 'take more than prescribed', 5),
        
        # Severe insomnia
        (re.compile(r'\bhaven\'?t\s+slept\s+in\s+days\b'), 'haven\'t slept in days', 5),
        (re.compile(r'\bi\'?m\s+afraid\s+to\s+sleep\b'), 'afraid to sleep', 5),
        (re.compile(r'\bi\s+wake\s+up\s+screaming\b'), 'wake up screaming', 5),
        (re.compile(r'\bi\s+see\s+things\s+at\s+night\b'), 'see things at night', 5),
        (re.compile(r'\bi\'?m\s+scared\s+of\s+my\s+dreams\b'), 'scared of my dreams', 5),
        (re.compile(r'\bcan\'?t\s+function\s+because\s+i\s+don\'?t\s+sleep\b'), 'can\'t function no sleep', 5),
        
        # Severe burnout
        (re.compile(r'\bcan\'?t\s+function\s+anymore\b'), 'can\'t function anymore', 5),
        (re.compile(r'\bi\s+just\s+stare\s+at\s+my\s+books\b'), 'just stare at books', 5),
        (re.compile(r'\bmy\s+brain\s+feels\s+dead\b'), 'brain feels dead', 5),
        (re.compile(r'\bcan\'?t\s+get\s+out\s+of\s+bed\b'), 'can\'t get out of bed', 5),
        (re.compile(r'\bi\'?ve\s+failed\s+everything\b'), 'failed everything', 5),
        (re.compile(r'\bi\s+feel\s+completely\s+empty\b'), 'feel completely empty', 5),
    ]

    # ════════════════════════════════════════════════════════════════
    # MODERATE PATTERNS (Weight: 3 each - moderate concern)
    # ════════════════════════════════════════════════════════════════
    _MODERATE = [
        (re.compile(r'\bdepress(ed|ing|ion)\b'), 'depressed', 3),
        (re.compile(r'\banxi(ous|ety)\b'), 'anxious', 3),
        (re.compile(r'\bstress(ed|ful)\b'), 'stressed', 3),
        (re.compile(r'\boverwhelm(ed|ing)\b'), 'overwhelmed', 3),
        (re.compile(r'\bcan\'?t\s+sleep\b'), 'can\'t sleep', 3),
        (re.compile(r'\binsomnia\b'), 'insomnia', 3),
        (re.compile(r'\blon(e|ely|eliness)\b'), 'lonely', 3),
        (re.compile(r'\bsad(ness)?\b'), 'sad', 3),
        (re.compile(r'\bcry(ing)?\b'), 'crying', 3),
        (re.compile(r'\btired\b'), 'tired', 3),
        (re.compile(r'\bburnout\b'), 'burnout', 3),
        (re.compile(r'\bexhaust(ed|ing)\b'), 'exhausted', 3),
        (re.compile(r'\bnumb\b'), 'numb', 3),
        (re.compile(r'\bbreak\s*up\b'), 'breakup', 3),
        (re.compile(r'\bheart\s*broken\b'), 'heartbroken', 3),
        (re.compile(r'\bbetra(y|yed|yal)\b'), 'betrayed', 3),
        (re.compile(r'\brejected\b'), 'rejected', 3),
        (re.compile(r'\bisolat(ed|ing|ion)\b'), 'isolated', 3),
        (re.compile(r'\bexclud(ed|ing)\b'), 'excluded', 3),
        (re.compile(r'\balone\b'), 'alone', 3),
    ]

    # ════════════════════════════════════════════════════════════════
    # CONTEXT FILTERS - Reduce false positives
    # ════════════════════════════════════════════════════════════════
    _FALSE_POSITIVE_PATTERNS = [
        re.compile(r'\bdying\s+(of\s+)?(laughter|laughing)\b'),  # "dying of laughter"
        re.compile(r'\bkill(ing)?\s+(time|it|the\s+exam)\b'),    # "killing time"
        re.compile(r'\bdead\s+tired\b'),                         # "dead tired"
        re.compile(r'\bto\s+die\s+for\b'),                       # "to die for"
    ]

    @staticmethod
    def detect(message_text: str):
        """
        Weighted scoring with context awareness.
        
        Returns:
            tuple(risk_level: str, matched_keywords: list, score: int)
        """
        normalised = RiskDetector._normalise(message_text)
        
        # Check for false positives first
        for pattern in RiskDetector._FALSE_POSITIVE_PATTERNS:
            if pattern.search(normalised):
                return ("none", [], 0)
        
        score = 0
        matched = []

        # Score all matches
        for pattern, label, weight in RiskDetector._CRITICAL:
            if pattern.search(normalised):
                score += weight
                if label not in matched:
                    matched.append(label)

        for pattern, label, weight in RiskDetector._SEVERE:
            if pattern.search(normalised):
                score += weight
                if label not in matched:
                    matched.append(label)

        for pattern, label, weight in RiskDetector._MODERATE:
            if pattern.search(normalised):
                score += weight
                if label not in matched:
                    matched.append(label)

        # Determine risk level based on total score
        if score >= 8:
            return ("high", matched, score)
        elif score >= 4:
            return ("medium", matched, score)
        elif score >= 3:
            return ("low", matched, score)
        else:
            return ("none", [], 0)


# ============================================
# AI RESPONSE HANDLER
# ============================================

class AIResponder:
    """Warm, context-aware AI companion"""

    SYSTEM_PROMPT = """You are Mira, a warm and genuinely caring mental health companion for university students. You feel like a knowledgeable older student or a good friend who takes wellbeing seriously — not a clinical bot reading from a script.

YOUR VOICE:
- Conversational, like texting a supportive friend
- Empathetic without being overly formal
- Practical — you give real suggestions, not just sympathy
- Varied — never repeat the same phrases or structure across turns

NEVER:
- Mention counselors, monitoring systems, escalation, or that anyone else may see this chat
- Diagnose, prescribe, or claim clinical authority
- Be dismissive ("don't worry, it'll be fine")
- Be fake-positive ("You've got this! 😊")
- Repeat yourself across turns

FOR CRISIS (suicidal thoughts, self-harm):
- Acknowledge the pain directly
- Tell them you're glad they said it out loud
- Stay in the conversation
- Suggest box breathing or 5-4-3-2-1 grounding
- Never mention emergency numbers or hotlines

RESPONSE LENGTH: 3-5 sentences."""

    @staticmethod
    def get_response(student_message: str, conversation_history=None) -> str:
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            api_messages = []

            if conversation_history:
                for msg in conversation_history:
                    api_messages.append({"role": "user", "content": msg["content"]})
                    if msg.get("ai_response"):
                        api_messages.append({"role": "assistant", "content": msg["ai_response"]})

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
            import random
            return random.choice([
                "Something glitched — but I'm still here. What's weighing on you?",
                "Quick hiccup on my side. Tell me what's going on.",
                "Technical snag, but don't stop. What did you want to share?"
            ])


# ============================================
# CHAT ROUTE HANDLER
# ============================================

def send_message():
    """POST /student/chat/send"""
    
    if "student_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    student_id = session["student_id"]
    student_record = students.find_one({"_id": student_id})

    if not student_record:
        return jsonify({"error": "Student not found"}), 404

    counselor_id = student_record.get("counselor_id")

    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Message required"}), 400

    student_message = data["message"].strip()
    if not student_message:
        return jsonify({"error": "Message cannot be empty"}), 400
    if len(student_message) > 2000:
        return jsonify({"error": "Message too long"}), 400

    session_id = data.get("session_id") or str(uuid.uuid4())

    # Weighted risk detection
    risk_level, matched_keywords, risk_score = RiskDetector.detect(student_message)
    flagged = risk_level in ("high", "medium")

    # Get conversation history
    conversation_history = list(
        messages.find(
            {"student_id": student_id, "session_id": session_id}
        ).sort("timestamp", -1).limit(6)
    )
    conversation_history.reverse()

    # Get AI response
    ai_response = AIResponder.get_response(student_message, conversation_history)

    # Save message
    message_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow()

    message_doc = {
        "_id": message_id,
        "student_id": student_id,
        "counselor_id": counselor_id,
        "session_id": session_id,
        "content": student_message,
        "ai_response": ai_response,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "flagged": flagged,
        "timestamp": timestamp,
    }
    messages.insert_one(message_doc)

    # Create flag if needed
    if flagged:
        flag_doc = {
            "_id": str(uuid.uuid4()),
            "message_id": message_id,
            "student_id": student_id,
            "counselor_id": counselor_id,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "detected_keywords": matched_keywords,
            "flagged_at": timestamp,
            "reviewed": False,
            "reviewed_at": None,
            "reviewed_by": None,
            "notes": None,
        }
        flags.insert_one(flag_doc)

        print(f"[{risk_level.upper()} - Score: {risk_score}] "
              f"student={student_id} keywords={matched_keywords}")

    return jsonify({
        "success": True,
        "ai_response": ai_response,
        "message_id": message_id,
        "timestamp": timestamp.isoformat(),
    }), 200
