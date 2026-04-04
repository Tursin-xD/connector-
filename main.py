import discord
from discord import Embed, Color, TextStyle
from discord.ui import View, Button, Modal, TextInput
from quart import Quart, request
import asyncio
import os
from datetime import datetime

# --- INITIALIZE APP ---
app = Quart(__name__)
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# --- GLOBAL DATA STORE ---
# This holds the latest info sent from your Roblox Server
game_info = {
    "name": "Waiting for Server...",
    "place_id": "0",
    "job_id": "0",
    "players": 0,
    "max_players": 0,
    "ping": "0",
    "player_list": "None",
    "last_lua": "-- No code queued"
}

# --- DISCORD UI COMPONENTS ---

class ExecuteModal(Modal, title='vLua Executor'):
    code_input = TextInput(label='Enter Lua Code', style=TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        game_info["last_lua"] = self.code_input.value
        await interaction.response.send_message("✅ Code queued for next Roblox poll.", ephemeral=True)

class GameControlView(View):
    def __init__(self):
        super().__init__(timeout=None)
        # 1. JOIN BUTTON: Uses the data received from Roblox
        join_url = f"roblox://experiences/start?placeId={game_info['place_id']}&gameInstanceId={game_info['job_id']}"
        self.add_item(Button(label="Join Game", url=join_url, style=discord.ButtonStyle.link))

    @discord.ui.button(label="UpdateCheck", style=discord.ButtonStyle.secondary)
    async def update_check(self, interaction: discord.Interaction, button: Button):
        # Private response to avoid "Channel Doom"
        status_msg = f"📊 **Live Stats:** {game_info['players']}/{game_info['max_players']} Players | Ping: {game_info['ping']}ms"
        await interaction.response.send_message(status_msg, ephemeral=True)

    @discord.ui.button(label="Execute", style=discord.ButtonStyle.danger)
    async def execute_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ExecuteModal())

# --- THE EMBED STRUCTURE ---
def create_status_embed():
    embed = Embed(
        title=f"🎮 {game_info['name']}",
        description="**Status:** `SERVER LIVE` 🟢",
        color=Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="🆔 Place ID", value=f"`{game_info['place_id']}`", inline=True)
    embed.add_field(name="🎫 Job ID", value=f"||`{game_info['job_id']}`||", inline=True)
    embed.add_field(name="👥 Players", value=f"`{game_info['players']}/{game_info['max_players']}`", inline=True)
    embed.add_field(name="📶 Ping", value=f"`{game_info['ping']}ms`", inline=True)
    embed.add_field(name="📜 Player List", value=f"```{game_info['player_list']}```", inline=False)
    embed.set_footer(text="Render Bridge • No-API Mode")
    return embed

# --- API ENDPOINTS FOR ROBLOX ---

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    """Roblox pushes data here"""
    data = await request.get_json()
    game_info.update(data)
    
    # Trigger Discord Broadcast
    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if channel:
        bot.loop.create_task(channel.send(embed=create_status_embed(), view=GameControlView()))
    return {"status": "success"}, 200

@app.route('/get-lua', methods=['GET'])
async def get_lua():
    """Roblox polls this to see if you pressed 'Execute'"""
    code = game_info["last_lua"]
    game_info["last_lua"] = "-- No code queued" # Reset after sending
    return {"code": code}, 200

# --- START THE APP ---
async def main():
    async with bot:
        await asyncio.gather(
            bot.start(os.getenv("DISCORD_TOKEN")),
            app.run_task(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
        )

if __name__ == "__main__":
    asyncio.run(main())
