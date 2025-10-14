import requests, os

def send_message(to, text):
    headers = {'X-Viber-Auth-Token': os.getenv("VIBER_BOT_TOKEN")}
    payload = {"receiver": to, "type": "text", "text": text}
    requests.post("https://chatapi.viber.com/pa/send_message", json=payload, headers=headers)
