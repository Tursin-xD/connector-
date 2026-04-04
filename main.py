import discord
import os
import asyncio
from quart import Quart, request
from datetime import datetime

app = Quart(__name__)
intents = discord.Intents.default()
intents.message_content = True 
bot = discord.Client(intents=intents)

# --- HOME PAGE (Fixes the 404 in your browser) ---
@app.route('/')
async def home():
    return "<h1>Bridge is Online</h1><p>Waiting for Roblox signals...</p>", 200

# --- THE ROBLOX ENDPOINT (Fixes the 404 in Roblox) ---
@app.route('/update-stats', methods=['POST'])
async def update_stats():
    data = await request.get_json()
    print(f"📥 Received data from Roblox: {data}")
    
    # Send to Discord
    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if channel:
        embed = discord.Embed(
            title=f"🎮 {data.get('name', 'Game')}",
            description=f"**Status:** {data.get('player_list', 'Active')}",
            color=discord.Color.green()
        )
        # You can add more fields here based on your Roblox data
        bot.loop.create_task(channel.send(embed=embed))
    
    return {"status": "success"}, 200

@app.before_serving
async def start_bot():
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
