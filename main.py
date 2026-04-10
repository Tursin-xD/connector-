import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import uvicorn
from quart import Quart, request
from datetime import datetime

# --- SETUP ---
app = Quart(__name__)
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store users wanting live DM updates {user_id: message_object}
active_subscribers = {}

# --- EMBED GENERATOR ---
def create_elite_embed(data, is_live=False):
    """Creates the high-quality red embed for both DMs and Channels."""
    embed_title = "📡 LIVE STATUS UPDATED" if is_live else "🎯 TARGET SERVER DETECTED"
    color = 0x00FF00 if is_live else 0xFF0000  # Green for live updates, Red for new alerts
    
    embed = discord.Embed(
        title=embed_title,
        description=f"**Game:** `{data.get('name', 'Unknown')}`",
        color=color,
        timestamp=datetime.utcnow()
    )
    
    # Grid layout for stats
    embed.add_field(name="👥 Players", value=f"`{data.get('players', 0)}/{data.get('max_players', 0)}`", inline=True)
    embed.add_field(name="🛰️ Ping", value=f"`{data.get('ping', 0)}ms`", inline=True)
    embed.add_field(name="🆔 Place ID", value=f"`{data.get('place_id', 'N/A')}`", inline=True)
    
    # 'fix' syntax highlighting makes text look technical
    player_list = data.get('player_list', 'No logs available')
    embed.add_field(
        name="📜 Server Logs", 
        value=f"```fix\n{player_list}\n```", 
        inline=False
    )
    
    embed.set_footer(text="System: Stable • yunito v2.1")
    return embed

def create_join_view(data):
    """Creates the interactive 'Execute/Join' button."""
    view = discord.ui.View(timeout=None)
    join_url = f"https://www.roblox.com/games/start?placeId={data.get('place_id')}&gameInstanceId={data.get('job_id')}"
    view.add_item(discord.ui.Button(label="🎮 Join & Execute", url=join_url, style=discord.ButtonStyle.link))
    return view

# --- SLASH COMMANDS ---
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`建设")

@bot.tree.command(name="status", description="Get auto-updating live logs in your DMs")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        embed = discord.Embed(title="🔄 Connecting to Roblox Bridge...", color=0xFF0000)
        dm_msg = await interaction.user.send(embed=embed)
        active_subscribers[interaction.user.id] = dm_msg
        await interaction.followup.send("✅ Live status feed activated in your DMs.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Error: Open your DMs in Privacy Settings!", ephemeral=True)

# --- WEB SERVER ROUTES ---
@app.route('/')
async def home():
    return "Bridge Online & Stable", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    data = await request.get_json()
    
    if bot.is_ready():
        # 1. Update Public Channel
        channel = bot.get_channel(int(os.getenv("CHANNEL_ID", 0)))
        if channel:
            bot.loop.create_task(channel.send(embed=create_elite_embed(data), view=create_join_view(data)))
        
        # 2. Update all active DM subscribers (the "Execute" updates)
        for user_id, msg in list(active_subscribers.items()):
            bot.loop.create_task(update_dm_safe(msg, data, user_id))
            
    return {"status": "success"}, 200

async def update_dm_safe(msg, data, user_id):
    try:
        await msg.edit(embed=create_elite_embed(data, is_live=True), view=create_join_view(data))
    except Exception:
        # Remove if user blocked bot or deleted message
        if user_id in active_subscribers:
            del active_subscribers[user_id]

# --- STARTUP LOGIC ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as: {bot.user}")

@app.before_serving
async def startup():
    # Delay to avoid Cloudflare 1015 on quick restarts
    await asyncio.sleep(2)
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    # Start Quart via Uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
