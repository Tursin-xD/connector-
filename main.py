import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import uvicorn
import httpx
from quart import Quart, request
from datetime import datetime

# --- INITIALIZATION ---
app = Quart(__name__)
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_subscribers = {}

# --- EMBED & VIEW BUILDERS ---

def create_elite_embed(data, is_live=False):
    embed_title = "📡 LIVE STATUS UPDATED" if is_live else "🎯 TARGET SERVER DETECTED"
    color = 0x00FF00 if is_live else 0xFF0000 
    
    embed = discord.Embed(
        title=embed_title,
        description=f"**Game Name:** `{data.get('name', 'Unknown Game')}`",
        color=color,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="👥 Players", value=f"`{data.get('players', 0)}/{data.get('max_players', 0)}`", inline=True)
    embed.add_field(name="🛰️ Ping", value=f"`{data.get('ping', 0)}ms`", inline=True)
    embed.add_field(name="🆔 Place ID", value=f"`{data.get('place_id', 'N/A')}`", inline=True)
    
    player_logs = data.get('player_list', 'No logs available')
    embed.add_field(name="📜 Server Logs", value=f"```fix\n{player_logs}\n```", inline=False)
    
    embed.set_footer(text="System: Stable • yunito v3.8")
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
    return embed

def create_join_view(data):
    view = discord.ui.View(timeout=None)
    join_url = f"https://www.roblox.com/games/start?placeId={data.get('place_id')}&gameInstanceId={data.get('job_id')}"
    view.add_item(discord.ui.Button(label="🎮 Join & Execute", url=join_url, style=discord.ButtonStyle.link))
    return view

# --- KEEP-ALIVE ---
@tasks.loop(minutes=10)
async def keep_alive_ping():
    url = "https://connector-x5ny.onrender.com/"
    try:
        async with httpx.AsyncClient() as client:
            await client.get(url)
    except: pass

# --- SLASH COMMANDS ---
@bot.tree.command(name="status", description="Get auto-updating live logs in your DMs")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        embed = discord.Embed(title="🔄 Connecting...", description="Waiting for Roblox data packet...", color=0xFFFFFF)
        dm_msg = await interaction.user.send(embed=embed)
        active_subscribers[interaction.user.id] = dm_msg
        await interaction.followup.send("✅ Live status feed activated in your DMs.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Error: Open your DMs!", ephemeral=True)

# --- WEB SERVER ROUTES ---
@app.route('/')
async def home(): return "Bridge Online", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    data = await request.get_json()
    print(f"📥 Received data from Roblox: {data.get('name')}") # Debug Log

    if bot.is_ready():
        # 1. Update Public Channel
        chan_id = os.getenv("CHANNEL_ID")
        if chan_id:
            channel = bot.get_channel(int(chan_id))
            if channel:
                bot.loop.create_task(channel.send(embed=create_elite_embed(data), view=create_join_view(data)))
            else:
                print(f"❌ Could not find channel with ID: {chan_id}")
        
        # 2. Update DM Subscribers
        for user_id, msg in list(active_subscribers.items()):
            bot.loop.create_task(update_dm_safe(msg, data, user_id))
            
    return {"status": "success"}, 200

async def update_dm_safe(msg, data, user_id):
    try:
        await msg.edit(embed=create_elite_embed(data, is_live=True), view=create_join_view(data))
        print(f"✅ DM updated for user {user_id}")
    except Exception as e:
        print(f"❌ DM Update Failed for {user_id}: {e}")
        if user_id in active_subscribers: del active_subscribers[user_id]

# --- STARTUP ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    if not keep_alive_ping.is_running(): keep_alive_ping.start()
    print(f"✅ Bot Online: {bot.user}")

@app.before_serving
async def startup():
    await asyncio.sleep(2)
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
