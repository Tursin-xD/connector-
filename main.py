import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from quart import Quart, request

# --- INITIALIZE ---
app = Quart(__name__)
intents = discord.Intents.default()
intents.message_content = True

# We use commands.Bot for slash command support
bot = commands.Bot(command_id=".", intents=intents)

# --- SLASH COMMANDS ---

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    # Calculate latency in milliseconds
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: `{latency}ms`")

@bot.tree.command(name="status", description="Get current Roblox server stats")
async def status(interaction: discord.Interaction):
    if not game_data:
        await interaction.response.send_message("❌ No active Roblox servers detected.", ephemeral=True)
        return
        
    await interaction.response.send_message(
        f"🎮 **Game:** {game_data.get('name')}\n"
        f"👤 **Players:** {game_data.get('players')}/{game_data.get('max_players')}\n"
        f"🛰️ **Status:** {game_data.get('status')}"
    )

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    try:
        # This SYNC step is what makes the / commands appear in Discord
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# --- WEB ROUTES ---
game_data = {}

@app.route('/')
async def home():
    return "<h1>Bridge UI Online</h1>", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    global game_data
    game_data = await request.get_json()
    # (Existing embed logic here...)
    return {"status": "success"}, 200

# --- STARTUP ---

@app.before_serving
async def startup():
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
