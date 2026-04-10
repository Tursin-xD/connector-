import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import uvicorn
from quart import Quart, request
from datetime import datetime

# --- INITIALIZATION ---
app = Quart(__name__)
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store users for live DM updates {user_id: message_object}
active_subscribers = {}

# --- EMBED & VIEW BUILDERS ---

def create_elite_embed(data, is_live=False):
    """Creates a high-quality embed with red/green themes."""
    embed_title = "📡 LIVE STATUS UPDATED" if is_live else "🎯 TARGET SERVER DETECTED"
    # Red (0xFF0000) for alerts, Green (0x00FF00) for live updates
    color = 0x00FF00 if is_live else 0xFF0000 
    
    embed = discord.Embed(
        title=embed_title,
        description=f"**Game Name:** `{data.get('name', 'Unknown Game')}`",
        color=color,
        timestamp=datetime.utcnow()
    )
    
    # Organized Stats Grid
    embed.add_field(name="👥 Players", value=f"`{data.get('players', 0)}/{data.get('max_players', 0)}`", inline=True)
    embed.add_field(name="🛰️ Ping", value=f"`{data.get('ping', 0)}ms`", inline=True)
    embed.add_field(name="🆔 Place ID", value=f"`{data.get('place_id', 'N/A')}`", inline=True)
    
    # Player Logs in 'fix' syntax highlighting
    player_logs = data.get('player_list', 'No logs available')
    embed.add_field(
        name="📜 Server Logs", 
        value=f"```fix\n{player_logs}\n```", 
        inline=False
    )
    
    embed.set_footer(text="System: Stable • yunito bridge v3.0")
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
    return embed

def create_join_view(data):
    """Adds the Execute/Join button."""
    view = discord.ui.View(timeout=None)
    join_url = f"https://www.roblox.com/games/start?placeId={data.get('place_id')}&gameInstanceId={data.get('job_id')}"
    view.add_item(discord.ui.Button(label="🎮 Join & Execute", url=join_url, style=discord.ButtonStyle.link))
    return view

# --- SLASH COMMANDS ---

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: `{latency}ms`", ephemeral=True)

@bot.tree.command(name="status", description="Receive auto-updating live logs in DMs")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        embed = discord.Embed(title="🔄 Connecting to Bridge...", description="Waiting for Roblox data packet...", color=0xFFFFFF)
        dm_msg = await interaction.user.send(embed=embed)
        
        # Save DM message object for later editing
        active_subscribers[interaction.user.id] = dm_msg
        await interaction.followup.send("✅ Live status activated! Check your DMs.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Error: Enable Direct Messages in Privacy Settings!", ephemeral=True)

@bot.tree.command(name="stop_updates", description="Stop the live DM feed")
async def stop_updates(interaction: discord.Interaction):
    if interaction.user.id in active_subscribers:
        del active_subscribers[interaction.user.id]
        await interaction.response.send_message("🛑 Live updates stopped.", ephemeral=True)
    else:
        await interaction.response.send_message("❓ No active status feed found.", ephemeral=True)

# --- WEB SERVER & API ---

@app.route('/')
async def home():
    return "<h1>Bridge UI Online</h1>", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    data = await request.get_json()
    
    if bot.is_ready():
        # 1. Update Public Logging Channel
        channel_id = os.getenv("CHANNEL_ID")
        if channel_id:
            channel = bot.get_channel(int(channel_id))
            if channel:
                bot.loop.create_task(channel.send(embed=create_elite_embed(data), view=create_join_view(data)))
        
        # 2. Update all active DM subscribers
        for user_id, msg in list(active_subscribers.items()):
            bot.loop.create_task(update_dm_safe(msg, data, user_id))
            
    return {"status": "success"}, 200

async def update_dm_safe(msg, data, user_id):
    try:
        await msg.edit(embed=create_elite_embed(data, is_live=True), view=create_join_view(data))
    except Exception:
        # If user blocked bot, clean up the dictionary
        if user_id in active_subscribers:
            del active_subscribers[user_id]

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    # Push slash commands to Discord
    await bot.tree.sync()
    print(f"✅ Bot Online: {bot.user}")

@app.before_serving
async def startup():
    # Delay prevents 1015 Cloudflare ban during rapid restarts
    await asyncio.sleep(2)
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

# --- EXECUTION ---

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
