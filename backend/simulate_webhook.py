import hmac
import hashlib
import json
import time
import urllib.request
from app.core.config import settings

def send_mock_webhook():
    # 1. Define the mock payload structure exactly as Meta sends it
    # Note the 'metadata.phone_number_id' which must match the clinic in our DB (1234567890)
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890", # Business Account ID
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550101",
                                "phone_number_id": "1234567890" # Matches Clinic.wa_phone_number_id
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": "15555551234"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "15555551234",
                                    "id": f"wamid.{int(time.time())}",
                                    "timestamp": str(int(time.time())),
                                    "text": {
                                        "body": "book"
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    # 2. Convert payload to JSON string
    payload_json = json.dumps(payload)

    # 3. Generate the required HMAC-SHA256 signature using the app secret
    secret = settings.WHATSAPP_APP_SECRET.encode('utf-8')
    signature = hmac.new(secret, payload_json.encode('utf-8'), hashlib.sha256).hexdigest()

    # 4. Send the POST request to the local server
    url = "http://localhost:8000/api/v1/webhook"
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={signature}"
    }

    print(f"Sending webhook payload to {url}...")
    req = urllib.request.Request(url, data=payload_json.encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            print(f"Response Status: {status_code}")
            if status_code == 200:
                print("✅ Webhook processed successfully! The server has routed it to the correct clinic.")
            else:
                print(f"❌ Failed with status: {status_code}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(f"Server response: {body}")
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}\nEnsure your FastAPI server is running on http://localhost:8000")

if __name__ == "__main__":
    send_mock_webhook()
