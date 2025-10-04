# crisis.py
from typing import Optional

# List of crisis-related keywords
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "self-harm",
    "depressed", "panic attack", "hopeless", "anxious"
]

# Safety message to return
SAFETY_MESSAGE = (
    "⚠️ It seems you might be going through a difficult time. "
    "Please consider reaching out to trained professionals immediately.\n\n"
    "📞 National Suicide Prevention Lifeline (USA): 1-800-273-TALK (8255)\n"
    "📱 Crisis Text Line: Text HOME to 741741\n"
    "🌍 If you are elsewhere, please search for local crisis helplines.\n\n"
    "Your life matters. You are not alone."
)

def check_for_crisis(user_message: str) -> Optional[str]:
    """
    Check if the user message contains any crisis keywords.
    Returns the safety message if detected, else None.
    """
    msg_lower = user_message.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword in msg_lower:
            return SAFETY_MESSAGE
    return None
