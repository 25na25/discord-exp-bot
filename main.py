import os
import pandas as pd
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button

# =========================
# TOKEN
# =========================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN is not set in environment variables")

# =========================
# intents
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CSV読み込み（安全版）
# =========================

SPECIAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=1840905945&single=true&output=csv"
BASE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=0&single=true&output=csv"

print("loading csv...")

try:
    special_df = pd.read_csv(SPECIAL_CSV_URL)
except Exception as e:
    print("SPECIAL CSV ERROR:", e)
    special_df = pd.DataFrame(columns=["特殊能力", "経験点"])

try:
    df = pd.read_csv(BASE_CSV_URL)
except Exception as e:
    print("BASE CSV ERROR:", e)
    df = pd.DataFrame(columns=["能力", "ミート", "パワー", "その他"])

# =========================
# テーブル構築
# =========================

SPECIAL_TABLE = {}
SPECIAL_OPTIONS = []

for _, row in special_df.iterrows():
    try:
        SPECIAL_TABLE[row["特殊能力"]] = int(row["経験点"])
    except:
        continue

for name in SPECIAL_TABLE.keys():
    SPECIAL_OPTIONS.append(discord.SelectOption(label=name, value=name))

MEAT_TABLE = {}
POWER_TABLE = {}
OTHER_TABLE = {}

for _, row in df.iterrows():
    try:
        ability = int(row["能力"])
        MEAT_TABLE[ability] = int(row["ミート"])
        POWER_TABLE[ability] = int(row["パワー"])
        OTHER_TABLE[ability] = int(row["その他"])
    except:
        continue

# =========================
# View
# =========================

class SpecialSkillView(View):

    def __init__(self, user_id, meat, power, run, defense, skill, mental):
        super().__init__(timeout=300)

        self.user_id = user_id
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
    # 他人操作完全ブロック
    # =========================

    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "このメニューはあなた専用です。",
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

        base = (
            MEAT_TABLE.get(self.meat, 0)
            + POWER_TABLE.get(self.power, 0)
            + OTHER_TABLE.get(self.run, 0)
            + OTHER_TABLE.get(self.defense, 0)
            + OTHER_TABLE.get(self.skill, 0)
            + OTHER_TABLE.get(self.mental, 0)
        )

        special = 0
        text = ""

        for s in self.selected_skills:
            v = SPECIAL_TABLE.get(s, 0)
            special += v
            text += f"{s} : {v}\n"

        total = base + special

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
            name="基礎",
            value=str(base),
            inline=False
        )

        if text:
            embed.add_field(
                name="特殊能力",
                value=f"{text}特殊能力計 : {special}",
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
        self.button.label = "完了"
        self.button.style = discord.ButtonStyle.gray

        await interaction.response.edit_message(
            content="✅ 計算完了",
            view=self
        )

        await interaction.followup.send(embed=embed)

# =========================
# command
# =========================

@bot.tree.command(name="exp", description="経験点計算")
async def exp(interaction: discord.Interaction, values: str):

    try:
        m, p, r, d, s, me = map(int, values.split())

        view = SpecialSkillView(
            interaction.user.id,
            m, p, r, d, s, me
        )

        await interaction.response.send_message(
            "特殊能力を選択してください",
            view=view
        )

    except:
        await interaction.response.send_message(
            "入力ミスです",
            ephemeral=True
        )

# =========================
# 起動
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

print("starting bot...")

bot.run(TOKEN)