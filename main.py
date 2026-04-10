import discord
from discord.ext import commands
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

# This dictionary keeps track of who needs DM updates
# Format: { user_id: message_object_to_edit }
active_subscribers = {}

# --- EMBED BUILDER ---

def create_elite_embed(data, is_live=False):
    """Creates a high-quality embed. Live updates get a green sidebar."""
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
    
    embed.set_footer(text="System: Stable • yunito bridge v3.2")
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
    return embed

def create_join_view(data):
    """Creates the 'Join & Execute' button for the embed."""
    view = discord.ui.View(timeout=None)
    join_url = f"https://www.roblox.com/games/start?placeId={data.get('place_id')}&gameInstanceId={data.get('job_id')}"
    view.add_item(discord.ui.Button(label="🎮 Join & Execute", url=join_url, style=discord.ButtonStyle.link))
    return view

# --- SLASH COMMANDS ---

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`建设", ephemeral=True)

@bot.tree.command(name="status", description="Start receiving auto-updating live logs in your DMs")
async def status(interaction: discord.Interaction):
    """This command triggers the DM part."""
    await interaction.response.defer(ephemeral=True)
    try:
        embed = discord.Embed(
            title="🔄 Initializing Live Feed...", 
            description="Waiting for the first data packet from Roblox...", 
            color=0xFFFFFF
        )
        # Send the initial DM
        dm_msg = await interaction.user.send(embed=embed)
        
        # Save the message object to our dictionary
        active_subscribers[interaction.user.id] = dm_msg
        
        await interaction.followup.send("✅ **Success!** Check your DMs. I will update that message whenever server stats change.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ **Error:** I can't DM you! Please enable 'Allow direct messages from server members' in your privacy settings.", ephemeral=True)

# --- WEB SERVER ROUTES ---

@app.route('/')
async def home():
    return "Bridge Status: Online", 200

@app.route('/get-lua', methods=['GET'])
async def get_lua():
    return "Route Active", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    """This is called by your Roblox script."""
    data = await request.get_json()
    
    if bot.is_ready():
        # 1. Update the Public Channel (if ID is provided)
        channel_id = os.getenv("CHANNEL_ID")
        if channel_id:
            channel = bot.get_channel(int(channel_id))
            if channel:
                bot.loop.create_task(channel.send(embed=create_elite_embed(data), view=create_join_view(data)))
        
        # 2. THE DM PART: Loop through all users who ran /status and edit their DM
        for user_id, msg in list(active_subscribers.items()):
            bot.loop.create_task(update_dm_safe(msg, data, user_id))
            
    return {"status": "success"}, 200

async def update_dm_safe(msg, data, user_id):
    """Edits the existing DM message instead of sending a new one."""
    try:
        await msg.edit(embed=create_elite_embed(data, is_live=True), view=create_join_view(data))
    except Exception as e:
        print(f"Could not update DM for {user_id}: {e}")
        # If the message was deleted or user blocked the bot, remove them from subscribers
        if user_id in active_subscribers:
            del active_subscribers[user_id]

# --- STARTUP LOGIC ---

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is logged in as {bot.user}")

@app.before_serving
async def startup():
    await asyncio.sleep(2) # Safety delay
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
