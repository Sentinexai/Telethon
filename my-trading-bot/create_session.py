from telethon.sync import TelegramClient
import time

api_id = 15880856
api_hash = '6e85de6b2c8cc0a9481dcf139c11dfb2'

with TelegramClient('railway_session', api_id, api_hash) as client:
    print("✅ Session created successfully")
    while True:
        time.sleep(10)
