import discord
import os
import asyncio
from quart import Quart, request
from datetime import datetime

# 1. Setup
app = Quart(__name__)
intents = discord.Intents.default()
intents.message_content = True # Ensure this is ON in Dev Portal
bot = discord.Client(intents=intents)

# 2. Web Routes (To keep Render happy and talk to Roblox)
@app.route('/')
async def home():
    return f"🟢 Bridge is Online. Current Time: {datetime.now()}", 200

@app.route('/status', methods=['GET'])
async def status():
    return {"bot_online": not bot.is_closed()}, 200

# 3. Discord Bot Events
@bot.event
async def on_ready():
    print(f'✅ SUCCESS: Logged in as {bot.user}')
    # Try to send a message to confirm it's working
    try:
        channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
        if channel:
            await channel.send("🚀 **Bot is now Online on Render!**")
    except Exception as e:
        print(f"Error sending boot message: {e}")

# 4. THE BRIDGE: This starts the bot when the web server starts
@app.before_serving
async def start_bot():
    print("🤖 Starting Discord Bot background task...")
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    # This part only runs if you run the file locally
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
