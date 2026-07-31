import requests

print("Testing plain requests.get to Africa's Talking...")
try:
    r = requests.get("https://api.sandbox.africastalking.com", timeout=10)
    print("SUCCESS:", r.status_code)
except Exception as e:
    print("FAILED:", e)

print("Testing plain requests.get to google.com...")
try:
    r = requests.get("https://www.google.com", timeout=10)
    print("SUCCESS:", r.status_code)
except Exception as e:
    print("FAILED:", e)
