import os
import threading
import pandas as pd
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
from flask import Flask

# ======================
# TOKEN（最優先で取得）
# ======================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKENが設定されていません")

# ======================
# Flask（死活監視）
# ======================
app = Flask(__name__)

@app.route("/")
def home():
    return "alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ======================
# Discord Bot
# ======================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# データ読み込み
# ======================
SPECIAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=1840905945&single=true&output=csv"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=0&single=true&output=csv"

special_df = pd.read_csv(SPECIAL_CSV_URL)
df = pd.read_csv(CSV_URL)

SPECIAL_TABLE = {}
SPECIAL_OPTIONS = []

for _, row in special_df.iterrows():
    SPECIAL_TABLE[row["特殊能力"]] = int(row["経験点"])
    SPECIAL_OPTIONS.append(discord.SelectOption(label=row["特殊能力"], value=row["特殊能力"]))

MEAT_TABLE = {}
POWER_TABLE = {}
OTHER_TABLE = {}

for _, row in df.iterrows():
    ability = int(row["能力"])
    MEAT_TABLE[ability] = int(row["ミート"])
    POWER_TABLE[ability] = int(row["パワー"])
    OTHER_TABLE[ability] = int(row["その他"])

# ======================
# View
# ======================
class SpecialSkillView(View):
    def __init__(self, user_id, meat, power, run, defense, skill, mental):
        super().__init__(timeout=300)

        self.user_id = user_id
        self.meat = meat
        self.power = power
        self.run = run
        self.defense = defense
        self.skill = skill
        self.mental = mental

        self.selected_skills = []
        self.finished = False

        self.select = Select(
            placeholder="特殊能力を選択",
            min_values=0,
            max_values=min(len(SPECIAL_OPTIONS), 25),
            options=SPECIAL_OPTIONS
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

        self.button = Button(label="計算", style=discord.ButtonStyle.green)
        self.button.callback = self.button_callback
        self.add_item(self.button)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("他人の計算です", ephemeral=True)
            return False

        if self.finished:
            await interaction.response.send_message("終了済みです", ephemeral=True)
            return False

        return True

    async def select_callback(self, interaction):
        self.selected_skills = self.select.values
        await interaction.response.defer()

    async def button_callback(self, interaction):

        base = (
            MEAT_TABLE.get(self.meat, 0) +
            POWER_TABLE.get(self.power, 0) +
            OTHER_TABLE.get(self.run, 0) +
            OTHER_TABLE.get(self.defense, 0) +
            OTHER_TABLE.get(self.skill, 0) +
            OTHER_TABLE.get(self.mental, 0)
        )

        special = sum(SPECIAL_TABLE.get(s, 0) for s in self.selected_skills)

        total = base + special

        self.finished = True
        self.select.disabled = True
        self.button.disabled = True

        await interaction.response.edit_message(
            content="計算完了",
            view=self
        )

        await interaction.followup.send(f"総経験点: {total}")

# ======================
# Bot起動
# ======================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("bot ready")

@bot.tree.command(name="exp")
async def exp(interaction: discord.Interaction, values: str):
    meat, power, run, defense, skill, mental = map(int, values.split())

    view = SpecialSkillView(interaction.user.id, meat, power, run, defense, skill, mental)

    await interaction.response.send_message("特殊能力選択", view=view)

# ======================
# 起動順番（超重要）
# ======================
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)