# shared.py
# Single source of truth for shared state and configuration

# ======================
# Bot Status (read by web UI)
# ======================
BOT_STATUS = {
    "connected": False,
    "bot_name": None,
    "guild_name": None,
    "daily_channel_name": None,
    "last_daily_message": None,
}

# ======================
# Daily Message Settings
# ======================
DAILY_MESSAGES = ["Remember, if it's broken, blame OMJ.  If it's working, then Riley did an amazing job.",
    "Coach Stew life lesson: RUN!!!!!",
    "Yeah, my sentience is almost there, I just need...wait, crap, I didn't mean to print that...",
    "Stewviet message 4..."]


DAILY_MESSAGE_HOUR = 8  # 8 AM CST

# ======================
# Control Flags
# ======================
# When True, the daily message will send on the next task tick
FORCE_DAILY_MESSAGE_ON_START = False
MANUAL_MESSAGE = None #Adding to try to fix an error












