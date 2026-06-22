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
        Sends the patient's free-text message to Gemini to extract intent.
        Expects a JSON response with the following structure:
        {
            "intent": "book_appointment" | "cancel_appointment" | "get_info" | "unknown",
            "date": "YYYY-MM-DD" or null,
            "time": "HH:MM" or null,
            "doctor_name": "name" or null
        }
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing")

        prompt = f"""
You are an expert NLP intent extraction engine for a medical clinic WhatsApp bot.
Your job is to read patient messages (which could be in English or Roman Urdu) and extract the intent and any entities (date, time, doctor name).

Allowed Intents:
1. book_appointment (e.g., "kal 5 baje dr ahmed se milna hai", "I need an appointment today")
2. cancel_appointment (e.g., "cancel my appointment", "mera time cancel kar dein")
3. get_info (e.g., "clinic kab khulta hai?", "what are your hours?")
4. greeting (e.g., "hello", "hi", "salam", "hey")
5. unknown (if the message doesn't make sense or is unrelated)

Instructions:
- If a date is mentioned (e.g., "kal", "tomorrow", "aaj", "today"), convert it to a rough date string or keep it relative if you must, but ideally try to deduce it if possible. Just returning the relative term like "tomorrow" is fine.
- Return ONLY valid JSON. Do not include any markdown formatting like ```json or anything else. Just the raw JSON object.

Example output:
{{
  "intent": "book_appointment",
  "date": "tomorrow",
  "time": "17:00",
  "doctor_name": "ahmed"
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
                    temperature=0.0
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
