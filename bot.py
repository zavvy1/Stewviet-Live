# Stewviet Beta
import os
import asyncio
import aiohttp
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from random import choice
from threading import Thread
from dotenv import load_dotenv

import discord
import requests
from discord.ext import tasks

# Load environment variables
load_dotenv()

# Timezone
CST = ZoneInfo("America/Chicago")

# Import shared configurations
import shared
from shared import (
    BOT_STATUS,
    DAILY_MESSAGES,
    DAILY_MESSAGE_HOUR,
    FORCE_DAILY_MESSAGE_ON_START,
    MANUAL_MESSAGE,
)

# Discord Client Setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Discord targets
DAILY_MESSAGE_GUILD_ID = 1135060782812516373
DAILY_MESSAGE_CHANNEL_ID = 1135060785270370376

# State tracking
last_daily_message_date = None
last_daily_log_hour = None

# ======================
# TWITCH CONFIG
# ======================
TWITCH_CLIENT_ID = "hp2mcz2rdnb4qsmqwtx2b7jpa5dn94"
TWITCH_CLIENT_SECRET = "s630nyo3xbryhu9gaol1svk11y7z1i"

twitch_token = None
twitch_token_expiry = 0

SERVERS = {
    1462847794577543190: {  # Riley's Test Bed
        "channel_id": 1462847795395428597,
        "role_id": 1462847968330911925,
        "streamers": [
            "ohnoitsriley",
        ]
    }
}

CHECK_INTERVAL = 60  # seconds
live_status = {}

# ======================
# TWITCH FUNCTIONS
# ======================
async def get_twitch_token():
    global twitch_token, twitch_token_expiry

    if twitch_token and time.time() < twitch_token_expiry:
        return twitch_token

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": TWITCH_CLIENT_ID,
                "client_secret": TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials"
            }
        ) as resp:
            data = await resp.json()
            twitch_token = data["access_token"]
            twitch_token_expiry = time.time() + data["expires_in"] - 60
            return twitch_token

async def check_twitch_stream(username):
    token = await get_twitch_token()

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers,
            params={"user_login": username},
        ) as resp:
            data = await resp.json()
            if data.get("data"):
                return data["data"][0]
            return None

# ======================
# OLLAMA FUNCTION
# ======================
def ask_ollama(prompt):
    try:
        r = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "qwen3:4b",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Stewviet, a Discord chatbot. Reply briefly and casually in 1–2 sentences."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 80
                }
            },
            timeout=120
        )
        data = r.json()
        return (
            data.get("message", {}).get("content", "")
            or data.get("response", "")
            or ""
        ).strip()
    except Exception as e:
        print(f"Ollama Error: {e}")
        return "⚠️ Error communicating with the AI model."

# ======================
# TASKS
# ======================
@tasks.loop(seconds=5)
async def manual_message_task():
    if shared.MANUAL_MESSAGE:
        guild = client.get_guild(DAILY_MESSAGE_GUILD_ID)
        if guild:
            channel = guild.get_channel(DAILY_MESSAGE_CHANNEL_ID)
            if channel:
                await channel.send(shared.MANUAL_MESSAGE)
        shared.MANUAL_MESSAGE = None

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_streams():
    for guild_id, cfg in SERVERS.items():
        guild = client.get_guild(guild_id)
        if not guild:
            continue

        channel = client.get_channel(cfg["channel_id"])
        if not channel:
            continue

        role_id = cfg.get("role_id")
        role_mention = f"<@&{role_id}>" if role_id else ""

        for name in cfg["streamers"]:
            key = f"{guild_id}:{name}"
            was_live = live_status.get(key, False)

            stream = await check_twitch_stream(name)

            if stream and not was_live:
                await channel.send(
                    f"{role_mention}\n" if role_mention else ""
                    f"🎥 **{name} is LIVE on Twitch!**\n"
                    f"🎮 **Game:** {stream['game_name']}\n"
                    f"📝 **Title:** {stream['title']}\n"
                    f"🔗 https://twitch.tv/{name}"
                )
                live_status[key] = True

            if not stream:
                live_status[key] = False

@tasks.loop(minutes=1)
async def daily_message_task():
    global last_daily_message_date, last_daily_log_hour

    now = datetime.now(CST)

    # Alive log every 3 hours
    if last_daily_log_hour != now.hour and now.hour % 3 == 0:
        print(f"[DailyTask] Alive check at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        last_daily_log_hour = now.hour

    # Only run at scheduled time unless forced
    if not shared.FORCE_DAILY_MESSAGE_ON_START:
        if now.hour != DAILY_MESSAGE_HOUR or now.minute != 0:
            return

    # Prevent duplicate sends
    if last_daily_message_date == now.date():
        return

    guild = client.get_guild(DAILY_MESSAGE_GUILD_ID)
    if not guild:
        print("[DailyTask] Guild not found")
        return

    channel = guild.get_channel(DAILY_MESSAGE_CHANNEL_ID)
    if not channel:
        print("[DailyTask] Channel not found")
        return

    # Send the message
    if DAILY_MESSAGES:
        message_text = choice(DAILY_MESSAGES)
        await channel.send(message_text)

    last_daily_message_date = now.date()
    shared.FORCE_DAILY_MESSAGE_ON_START = False
    BOT_STATUS["last_daily_message"] = now.strftime("%Y-%m-%d %H:%M:%S %Z")

    print("[DailyTask] Daily message sent")

# ======================
# EVENTS
# ======================
@client.event
async def on_ready():
    print(f"LOGGED IN AS: {client.user}")
    
    BOT_STATUS["connected"] = True
    BOT_STATUS["bot_name"] = str(client.user)

    guild = client.get_guild(DAILY_MESSAGE_GUILD_ID)
    if guild:
        BOT_STATUS["guild_name"] = guild.name
        channel = guild.get_channel(DAILY_MESSAGE_CHANNEL_ID)
        if channel:
            BOT_STATUS["daily_channel_name"] = channel.name

    # Start loop tasks if not already running
    if not manual_message_task.is_running():
        manual_message_task.start()

    if not check_streams.is_running():
        check_streams.start()

    if not daily_message_task.is_running():
        daily_message_task.start()

    # Start web dashboard thread
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!chat"):
        user_prompt = message.content[6:].strip()

        async with message.channel.typing():
            # Safely run the synchronous requests call in an executor thread
            response = await asyncio.to_thread(ask_ollama, user_prompt)

        if not response:
            response = "⚠️ No response from model."

        await message.channel.send(response)

# ======================
# WEB SERVER
# ======================
def run_web():
    try:
        from web import app
        app.run(host="0.0.0.0", port=5000)
    except ImportError:
        print("[Web Error] Could not import 'app' from 'web.py'. Make sure 'web.py' exists in this directory.")

# ======================
# START BOT
# ======================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
print("WORKING DIR:", os.getcwd())

if DISCORD_TOKEN:
    client.run(DISCORD_TOKEN)
else:
    print("❌ ERROR: DISCORD_TOKEN not found in your environment (.env file).")