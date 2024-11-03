from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
import os
from http_file_wrapper import HTTPFileWrapper

import logging
logging.basicConfig(format='[%(levelname) %(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

# 从环境变量获取 Telegram API ID 和 Hash
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# handle start message
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Send a message when the command /start is issued."""
    await event.respond('Hi!')

# handle /download command
@client.on(events.NewMessage(pattern='/download'))
async def download(event):
    """Download the file from the given link and send it to the user."""
    # get the link from the message
    # 获取所有 URL 实体
    found = False
    for entity in event.message.entities or []:
        if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
            found = True
            # 提取 URL 文本
            url = event.message.text[entity.offset:entity.offset + entity.length]
            await event.respond('Downloading url: ' + url)
            file = HTTPFileWrapper(url)
            await client.send_file(event.chat_id, file, supports_streaming=True)
    if not found:
        await event.respond('No URL found in the message.')
 
def main():
    """Start the bot."""
    client.run_until_disconnected()

if __name__ == '__main__':
    main()