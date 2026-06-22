import requests

# We already know your WABA ID from your earlier logs
WABA_ID = "1005544191909726"

# TODO: Copy the Temporary Access Token from your .env file and paste it inside the quotes below
ACCESS_TOKEN = "EAAXKuZCf6F0UBRmMd8tuTs0xZBKTg0h2e8O0YxLfXfR3RY4dJRZB2OTWpVOVXGqDxZCiMjbAZAJCwZC5lWqoHh2MarhlHBkxNZAPSKYbPEeYYPZAl9PztFHWl5GFJZC1eD8h59PmADYmNCD7ltWI0kAOe0FAeUH5N2onCUcicg1gEVZA4bB4BfcCOHwPwLFcb1SxbUbwV54MGiYyQhZCNiKGCUt0v1oZBLYEH4yccXG6AM6M5zTw6WvivXbH82NMwfe5BninMKevHm8g2InoYKZCHU2VCuujh"

url = f"https://graph.facebook.com/v21.0/{WABA_ID}/subscribed_apps"
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

print("Attempting to force Webhook Subscription...")
response = requests.post(url, headers=headers)

print("Meta's Response:")
print(response.json())