from telethon import TelegramClient, events
import os

import logging
logging.basicConfig(format='[%(levelname) %(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

# 从环境变量获取 Telegram API ID 和 Hash
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")

client = TelegramClient('bot', api_id, api_hash)

# handle start message
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Send a message when the command /start is issued."""
    await event.respond('Hi!')

client.start(bot_token=bot_token)
client.run_until_disconnected()