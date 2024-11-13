from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
import os
from http_file_wrapper import HTTPFileWrapper
from telethon_file_wrapper import TelethonFileWrapper
import zipfile
from itertools import groupby

#import logging
#logging.basicConfig(format='[%(levelname) %(asctime)s] %(name)s: %(message)s',
#                    level=logging.WARNING)

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

@client.on(events.NewMessage(pattern='/testunzip'))
async def unziptest(event):
    # await client.send_file(event.chat_id, 'README.md')
    print(zipfile.is_zipfile('large.zip'))
    zip_file = zipfile.ZipFile('large.zip')
    #for name in zip_file.namelist():
    #    if not name.endswith('/'):
    #        await client.send_file(event.chat_id, zip_file.open(name))
    zip_file.printdir()
    path = zipfile.Path(zip_file)
    for entry in path.iterdir():
        print(entry.name)
        print(entry.at)
        print(entry.root.namelist())
        album = []
        for entry2 in entry.iterdir():
            print(entry2.name)
            print(entry2.at)
            suffix = os.path.splitext(entry2.at)[1]
            print(suffix)
            # print(entry2.root.namelist())
            if(suffix == '.jpg'):
                album.append(zip_file.open(entry2.at))
            # await client.send_file(event.chat_id, zip_file.open(entry2.at))
        # await client.send_file(event.chat_id, album)
    await extractall(event, path, zip_file)
async def extractall(event, path, zip_file):
    for entry in path.iterdir():
        if(entry.is_dir()):
            await extractall(event, entry, zip_file)
    files = []
    for entry in path.iterdir():
        if(entry.is_file()):
            files.append(entry)
    files.sort(key=lambda file: os.path.splitext(file.at)[1])
    # album = [file.open() for file in files]
    for suffix, album in groupby(files, key=lambda file: os.path.splitext(file.at)[1]):
        album = [zip_file.open(file.at) for file in album]
        await client.send_file(event.chat_id, album)

@client.on(events.NewMessage)
async def handle_files(event):
    if event.document:
        await client.send_message(event.chat_id, 'Received file: ' + event.document.attributes[0].file_name)
        await client.download_file(event.document, 'downloads/' + event.document.attributes[0].file_name)
        await client.send_file(event.chat_id, TelethonFileWrapper(client, event.document))
    if False:
        file_wrapper = TelethonFileWrapper(client, event.document)
        if zipfile.is_zipfile(file_wrapper):
            await event.respond('这是一个 zip 文件，开始解压...')
            
        zip_file = zipfile.ZipFile(file_wrapper)
        for name in zip_file.namelist():
            await event.respond(f"解压文件: {name}")
            if not name.endswith('/'):
                await client.send_file(event.chat_id, zip_file.open(name))
        await event.respond('所有文件已解压并发送给您！')

def main():
    """Start the bot."""
    client.run_until_disconnected()

if __name__ == '__main__':
    main()