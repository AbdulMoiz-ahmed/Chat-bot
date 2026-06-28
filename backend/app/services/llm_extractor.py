import json
import logging
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger("llm_extractor")

if not settings.GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not configured in settings!")

class LLMExtractor:
    @staticmethod
    async def extract_intent(text: str = "", audio_path: str = None, clinic_context: dict = None) -> dict:
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

        clinic_info = ""
        if clinic_context:
            doc_info = "\n".join([f"- Dr. {d['name']} ({d['specialty']}): {d['bio']}" for d in clinic_context.get("doctors", [])])
            clinic_info = f"""
Clinic Name: {clinic_context.get('name')}
Clinic Address: {clinic_context.get('address')}
Working Hours: {clinic_context.get('working_hours')}
General Info: {clinic_context.get('general_info')}

Available Doctors at this clinic:
{doc_info}

CRITICAL RULE: You MUST strictly use the above Clinic and Doctor information to answer patient queries. Do NOT invent, hallucinate, or guess addresses, names, hours, or any other facts not provided above.
CRITICAL RULE 2: If the patient asks questions completely unrelated to healthcare, medicine, or this specific clinic (e.g., coding, politics, car repair, general knowledge trivia), you MUST politely decline to answer. State that you are a medical assistant for this clinic and pivot back to asking how you can help them with their healthcare needs.
"""
        else:
            clinic_info = "You are a highly empathetic, professional medical clinic receptionist and virtual assistant."

        prompt = f"""
{clinic_info}

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
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            contents = [prompt]
            if audio_path:
                logger.info(f"Uploading audio file to Gemini: {audio_path}")
                audio_file = client.files.upload(file=audio_path)
                contents.append(audio_file)
            
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=contents,
                config=types.GenerateContentConfig(
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
