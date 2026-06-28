import json
import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger("llm_extractor")

# Initialize Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not configured in settings!")

class LLMExtractor:
    @staticmethod
    async def extract_intent(text: str) -> dict:
        """
        Sends the patient's free-text message to Gemini to extract intent AND generate
        a contextual natural-language response matching the patient's language (Urdu, Roman Urdu, Hindi, English, etc.).
        
        Expects a JSON response with the following structure:
        {
            "intent": "book_appointment" | "cancel_appointment" | "get_info" | "greeting" | "chit_chat" | "unknown",
            "date": "YYYY-MM-DD" or "tomorrow" or null,
            "time": "HH:MM" or null,
            "doctor_name": "name" or null,
            "conversational_response": "Friendly personalized response in the user's input language/script answering their specific message. Always sound like an expert medical clinic assistant."
        }
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing")

        prompt = f"""
You are a highly empathetic, professional medical clinic receptionist and virtual assistant.
Your job is to read incoming patient messages, detect their language and script (e.g., English, Roman Urdu, Urdu script, Hindi, Spanish, etc.), extract key intent fields, and write a natural conversational response in their EXACT same language/style.

Always attempt to reply contextually and helpfully to the patient's actual message. NEVER output basic, robotic "I don't understand" responses if you can help it. If they want to book or inquire about an appointment, guide them smoothly.

Intents:
1. book_appointment: Patient wants to book or schedule a visit (e.g., "appointment chahiye", "milna hai dr ahmed se", "I want to schedule").
2. cancel_appointment: Patient wants to cancel/manage booking.
3. get_info: Patient asks about hours, fees, location, services, etc.
4. greeting: Short greeting ("salam", "hello", "hi").
5. chit_chat: Basic chatting, asking how you are, etc.
6. unknown: If the message is completely spam, nonsense, or highly abusive.

Instructions for "conversational_response":
- Detect the input language & script. Reply in that script (e.g. if they write in Urdu script, write Urdu script; if Roman Urdu like "salam doctor saab", write in Roman Urdu; if English, write in English).
- Keep it friendly, empathetic, and professional.
- For book_appointment or cancel_appointment intents, acknowledge their request nicely and let them know you are opening the selector panel to help them choose a doctor/slot.

Return ONLY valid JSON. Do not include any markdown formatting like ```json or anything else. Just the raw JSON object.

Example output structure:
{{
  "intent": "book_appointment",
  "date": "tomorrow",
  "time": "17:00",
  "doctor_name": "ahmed",
  "conversational_response": "Salam! Main aapki appointment book karne mein madad karta hoon. Specialty aur doctor select karne ke liye niche click karein."
}}

Patient Message:
"{text}"
"""
        
        try:
            # We use gemini-2.5-flash
            model = genai.GenerativeModel('gemini-2.5-flash')
            # Set response_mime_type to application/json to enforce JSON output natively
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            
            response_text = response.text.strip()
            # Failsafe: if the model still wraps in markdown despite application/json
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            data = json.loads(response_text)
            return data
            
        except Exception as e:
            logger.error(f"Failed to extract intent via Gemini: {e}")
            raise
