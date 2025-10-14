from fastapi import FastAPI, Request, Form
from guzo_booking_bot.message_router import process_message

app = FastAPI()

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    msg = data["message"]
    process_message("telegram", msg["chat"]["id"], msg["text"])
    return {"ok": True}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    process_message("whatsapp", From, Body)
    return "ok"

@app.post("/webhook/sms")
async def sms_webhook(From: str = Form(...), Body: str = Form(...)):
    process_message("sms", From, Body)
    return "ok"
