import discord
import os
import asyncio
from quart import Quart, request

app = Quart(__name__)
intents = discord.Intents.default()
intents.message_content = True 
bot = discord.Client(intents=intents)

# This stores the latest Roblox data
game_data = {}

@app.route('/')
async def home():
    return "<h1>Bridge is Online</h1>", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    global game_data
    game_data = await request.get_json()
    
    # Trigger the Discord message in the background
    asyncio.create_task(send_to_discord(game_data))
    return {"status": "success"}, 200

async def send_to_discord(data):
    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if channel and bot.is_ready():
        embed = discord.Embed(
            title=f"🎮 {data.get('name', 'Infect Game Detected')}",
            description=f"**Players:** {data.get('players')}/{data.get('max_players')}\n**Status:** {data.get('player_list')}",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

@app.before_serving
async def startup():
    # Force the bot to start alongside the web server
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
