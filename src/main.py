from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
import os
from http_file_wrapper import HTTPFileWrapper
import zipfile

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

# handle /unzip command
@client.on(events.NewMessage(pattern='/unzip'))
async def unzip(event):
    """Unzip the file from the given link and send it to the user."""
    # get the link from the message
    # 获取所有 URL 实体
    found = False
    for entity in event.message.entities or []:
        if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
            found = True
            # 提取 URL 文本
            url = event.message.text[entity.offset:entity.offset + entity.length]
            await event.respond('Unzipping url: ' + url)
            file = HTTPFileWrapper(url)
            # 判断是否是压缩文件
            if zipfile.is_zipfile(file):
                await client.send_message(event.chat_id, 'This is a zip file.')
                # 读取压缩文件的目录发送给用户
                zip_file = zipfile.ZipFile(file)
                for name in zip_file.namelist():
                    await client.send_message(event.chat_id, name)
                # 将所有压缩文件发送给用户
                for name in zip_file.namelist():
                    if not name.endswith('/'):
                        await client.send_file(event.chat_id, zip_file.open(name))
    if not found:
        await event.respond('No URL found in the message.')
def main():
    """Start the bot."""
    client.run_until_disconnected()

if __name__ == '__main__':
    main()