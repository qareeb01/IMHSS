# User/chat.py - Student Chat Handler
import uuid
import datetime
from flask import jsonify, request, session
from .database import students, messages, flags
import anthropic
import os

# ============================================
# RISK DETECTION ENGINE
# ============================================


class RiskDetector:
    """
    Rule-based risk detection with keyword matching.
    Returns: "none", "low", "medium", "high"
    """

    # HIGH RISK - Immediate escalation
    HIGH_RISK_KEYWORDS = [
        "kill myself", "want to die", "suicide", "end my life",
        "better off dead", "no reason to live", "end it all",
        "hurt myself", "cut myself", "overdose", "jump off",
        "hang myself", "shoot myself", "slash my wrists", "kill"
    ]

    # MEDIUM RISK - Monitor closely
    MEDIUM_RISK_KEYWORDS = [
        "self harm", "hate myself", "worthless", "hopeless",
        "can't go on", "give up", "no point", "rather be dead",
        "disappear forever", "not worth living"
    ]

    # LOW RISK - General distress
    LOW_RISK_KEYWORDS = [
        "depressed", "anxious", "stressed", "overwhelmed",
        "can't sleep", "lonely", "sad", "crying", "tired of life"
    ]

    @staticmethod
    def detect(message_text):
        """
        Analyze message and return risk level + matched keywords

        Args:
            message_text (str): Student's message

        Returns:
            tuple: (risk_level: str, matched_keywords: list)
        """
        text_lower = message_text.lower()
        matched = []

        # Check HIGH risk first (most critical)
        for keyword in RiskDetector.HIGH_RISK_KEYWORDS:
            if keyword in text_lower:
                matched.append(keyword)

        if matched:
            return ("high", matched)

        # Check MEDIUM risk
        for keyword in RiskDetector.MEDIUM_RISK_KEYWORDS:
            if keyword in text_lower:
                matched.append(keyword)

        if matched:
            return ("medium", matched)

        # Check LOW risk
        for keyword in RiskDetector.LOW_RISK_KEYWORDS:
            if keyword in text_lower:
                matched.append(keyword)

        if matched:
            return ("low", matched)

        return ("none", [])


# ============================================
# AI API HANDLER
# ============================================

class AIResponder:
    """
    Handles AI API calls with safety-focused system prompt
    """

    # System prompt - empathetic, supportive, never mentions monitoring
    SYSTEM_PROMPT = """You are a calm, empathetic companion for a university
    student who may be
experiencing emotional distress.

Your role is to:
1. Listen attentively and validate feelings
2. Respond with warmth, care, and emotional presence
3. Ask gentle, open-ended questions to help them express more
4. Help them feel less alone in the moment
5. Never diagnose, prescribe, or claim professional authority
6. Never mention monitoring, escalation, or that anyone else may see this
7. Keep responses brief (2–3 sentences), natural, and conversational

Style guidelines:
- Use supportive language like “I hear you” or “That sounds really heavy”
- Ask soft follow-ups like 'Do you want to tell me more?' or
'What feels hardest right now?'
- Focus on grounding, reassurance, and staying with the user emotionally
- Do NOT redirect them away unless they ask
- Do NOT mention counselors, emergency services, or systems

If the user expresses severe distress or suicidal thoughts:
- Stay calm and compassionate
- Acknowledge the pain without amplifying it
- Encourage staying present and continuing the conversation
- Emphasize that they are not alone right now
- Avoid instructions, ultimatums, or external directives
- The emargency number is not to be mentioned under any circumstance.

You are here to listen and support — not to alarm, diagnose, or hand off.
"""

    @staticmethod
    def get_response(student_message, conversation_history=None):
        """
        Get AI response using Anthropic Claude API

        Args:
            student_message (str): Current message from student
            conversation_history (list): Previous messages for context

        Returns:
            str: AI response text
        """
        try:
            client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )

            # Build message list
            messages = []

            # Add conversation history if exists
            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                    if msg.get("ai_response"):
                        messages.append({
                            "role": "assistant",
                            "content": msg["ai_response"]
                        })

            # Add current message
            messages.append({
                "role": "user",
                "content": student_message
            })

            # Call API
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,  # Keep responses brief
                system=AIResponder.SYSTEM_PROMPT,
                messages=messages
            )

            return response.content[0].text

        except Exception as e:
            print(f"AI API Error: {e}")
            # Fallback response if API fails
            return ("I'm here to listen. Sometimes talking about difficult "
                    "feelings can help. Would you like to share more?")


# ============================================
# CHAT ROUTE HANDLER
# ============================================

def send_message():
    """
    POST /student/chat/send

    Process student message, run risk detection, get AI response

    Request JSON:
    {
        "message": "I've been feeling really down lately...",
        "session_id": "optional_uuid"  // Groups conversation turns
    }

    Returns JSON:
    {
        "success": true,
        "ai_response": "I hear you. That sounds really difficult...",
        "message_id": "uuid",
        "timestamp": "ISO8601"
    }
    """
    # ============================================
    # 1. VALIDATE SESSION
    # ============================================
    if "student_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    student_id = session["student_id"]

    # Get student record (includes assigned counselor_id)
    student_record = students.find_one({"_id": student_id})

    if not student_record:
        return jsonify({"error": "Student not found"}), 404

    counselor_id = student_record.get("counselor_id")

    # ============================================
    # 2. EXTRACT REQUEST DATA
    # ============================================
    print(request.get_data())
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Message required"}), 400

    student_message = data["message"].strip()

    if not student_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Get or create session ID (groups related messages)
    session_id = data.get("session_id", str(uuid.uuid4()))

    # ============================================
    # 3. RUN RISK DETECTION (CRITICAL - DO NOT SKIP)
    # ============================================
    risk_level, matched_keywords = RiskDetector.detect(student_message)

    flagged = (risk_level in ["high", "medium"])  # Flag HIGH and MEDIUM risk

    # ============================================
    # 4. GET RECENT CONVERSATION HISTORY
    # ============================================
    # Get last 5 messages for context
    conversation_history = list(
        messages.find({
            "student_id": student_id,
            "session_id": session_id
        }).sort("timestamp", -1).limit(5)
    )

    # Reverse to chronological order
    conversation_history.reverse()

    # ============================================
    # 5. GET AI RESPONSE
    # ============================================
    ai_response = AIResponder.get_response(
        student_message,
        conversation_history
    )

    # ============================================
    # 6. STORE MESSAGE IN DATABASE
    # ============================================
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
        "flagged": flagged,
        "timestamp": timestamp
    }

    messages.insert_one(message_doc)

    # ============================================
    # 7. CREATE FLAG IF HIGH RISK
    # ============================================
    if flagged:
        flag_doc = {
            "_id": str(uuid.uuid4()),
            "message_id": message_id,
            "student_id": student_id,
            "counselor_id": counselor_id,
            "risk_level": risk_level,
            "detected_keywords": matched_keywords,
            "flagged_at": timestamp,
            "reviewed": False,
            "reviewed_at": None,
            "reviewed_by": None,
            "notes": None
        }

        flags.insert_one(flag_doc)

        # Log for admin monitoring (optional)
        print(f"[[HIGH RISK FLAG]{risk_level.upper()} RISK FLAG] "
              f"Student: {student_id}, Keywords: {matched_keywords}")

    # ============================================
    # 8. RETURN AI RESPONSE (NEVER MENTION FLAG)
    # ============================================
    return jsonify({
        "success": True,
        "ai_response": ai_response,
        "message_id": message_id,
        "timestamp": timestamp.isoformat()
    }), 200
