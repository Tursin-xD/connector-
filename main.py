import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import uvicorn
from quart import Quart, request

app = Quart(__name__)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

game_data = {}

@bot.tree.command(name="ping", description="Check latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@app.route('/')
async def home():
    return "<h1>Bridge UI Online</h1>", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    global game_data
    game_data = await request.get_json()
    asyncio.create_task(send_detailed_embed(game_data))
    return {"status": "success"}, 200

async def send_detailed_embed(data):
    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if channel and bot.is_ready():
        embed = discord.Embed(title=f"📡 Infect Game: {data.get('name')}", color=0xFF0000)
        embed.add_field(name="📊 Stats", value=f"Players: `{data.get('players')}/{data.get('max_players')}`", inline=True)
        embed.add_field(name="🕵️ Activity", value=f"```{data.get('player_list')}```", inline=False)
        
        view = discord.ui.View(timeout=None)
        join_url = f"https://www.roblox.com/games/start?placeId={data.get('place_id')}&gameInstanceId={data.get('job_id')}"
        view.add_item(discord.ui.Button(label="🎮 Join", url=join_url))
        await channel.send(embed=embed, view=view)

async def run_bot():
    await bot.start(os.getenv("DISCORD_TOKEN"))

@bot.event
async def on_ready():
    await bot.tree.sync()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
