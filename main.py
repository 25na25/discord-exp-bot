import os
import threading
import pandas as pd
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
from flask import Flask

# =========================
# Flask（Render用死活監視）
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "alive"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# TOKEN
# =========================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN is not set in environment variables")

# =========================
# Discord intents
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# データ読み込み
# =========================

SPECIAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=1840905945&single=true&output=csv"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=0&single=true&output=csv"

special_df = pd.read_csv(SPECIAL_CSV_URL)
df = pd.read_csv(CSV_URL)

SPECIAL_TABLE = {}
SPECIAL_OPTIONS = []

for _, row in special_df.iterrows():
    SPECIAL_TABLE[row["特殊能力"]] = int(row["経験点"])

for name in SPECIAL_TABLE.keys():
    SPECIAL_OPTIONS.append(discord.SelectOption(label=name, value=name))

MEAT_TABLE = {}
POWER_TABLE = {}
OTHER_TABLE = {}

for _, row in df.iterrows():
    ability = int(row["能力"])
    MEAT_TABLE[ability] = int(row["ミート"])
    POWER_TABLE[ability] = int(row["パワー"])
    OTHER_TABLE[ability] = int(row["その他"])

# =========================
# View
# =========================

class SpecialSkillView(View):

    def __init__(self, user_id, meat, power, run, defense, skill, mental):
        super().__init__(timeout=300)

        self.user_id = user_id
        self.message_id = None
        self.finished = False

        self.meat = meat
        self.power = power
        self.run = run
        self.defense = defense
        self.skill = skill
        self.mental = mental

        self.selected_skills = []

        self.select = Select(
            placeholder="特殊能力を選択",
            min_values=0,
            max_values=min(len(SPECIAL_OPTIONS), 25),
            options=SPECIAL_OPTIONS
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

        self.button = Button(
            label="計算",
            style=discord.ButtonStyle.green
        )
        self.button.callback = self.button_callback
        self.add_item(self.button)

    # =========================
    # 所有者制御（最重要）
    # =========================

    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "これはあなたの操作ではありません。",
                ephemeral=True
            )
            return False

        if self.finished:
            await interaction.response.send_message(
                "この計算はすでに完了しています。",
                ephemeral=True
            )
            return False

        return True

    # =========================
    # select
    # =========================

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_skills = self.select.values
        await interaction.response.defer()

    # =========================
    # button
    # =========================

    async def button_callback(self, interaction: discord.Interaction):

        base_total = (
            MEAT_TABLE.get(self.meat, 0)
            + POWER_TABLE.get(self.power, 0)
            + OTHER_TABLE.get(self.run, 0)
            + OTHER_TABLE.get(self.defense, 0)
            + OTHER_TABLE.get(self.skill, 0)
            + OTHER_TABLE.get(self.mental, 0)
        )

        special_total = 0
        special_text = ""

        for s in self.selected_skills:
            v = SPECIAL_TABLE.get(s, 0)
            special_total += v
            special_text += f"{s} : {v}\n"

        total = base_total + special_total

        embed = discord.Embed(
            title="野手経験点計算結果",
            color=0x2ecc71
        )

        embed.add_field(
            name="能力値",
            value=f"{self.meat}-{self.power}-{self.run}-{self.defense}-{self.skill}-{self.mental}",
            inline=False
        )

        embed.add_field(
            name="基礎能力",
            value=str(base_total),
            inline=False
        )

        if special_text:
            embed.add_field(
                name="特殊能力",
                value=f"{special_text}特殊能力計 : {special_total}",
                inline=False
            )

        embed.add_field(
            name="総経験点",
            value=str(total),
            inline=False
        )

        # UIロック
        self.finished = True
        self.select.disabled = True
        self.button.disabled = True
        self.button.label = "計算済"
        self.button.style = discord.ButtonStyle.gray

        await interaction.response.edit_message(
            content="✅ 計算完了",
            view=self
        )

        await interaction.followup.send(embed=embed)

# =========================
# command
# =========================

@bot.tree.command(name="exp", description="野手経験点を計算します")
@app_commands.describe(values="ミート パワー 走力 守備 小技 精神")
async def exp(interaction: discord.Interaction, values: str):

    try:
        meat, power, run, defense, skill, mental = map(int, values.split())

        view = SpecialSkillView(
            interaction.user.id,
            meat, power, run, defense, skill, mental
        )

        await interaction.response.send_message(
            "特殊能力を選択してください",
            view=view
        )

    except:
        await interaction.response.send_message(
            "入力形式が正しくありません。",
            ephemeral=True
        )

# =========================
# 起動
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} でログインしました")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)