import os
import asyncio
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
    raise RuntimeError("TOKEN is not set")

# =========================
# intents
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CSV URL
# =========================

SPECIAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=1840905945&single=true&output=csv"
BASE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=0&single=true&output=csv"

# =========================
# グローバルデータ（キャッシュ）
# =========================

SPECIAL_TABLE = {}
SPECIAL_OPTIONS = []

MEAT_TABLE = {}
POWER_TABLE = {}
OTHER_TABLE = {}

# =========================
# 初期ロード
# =========================

def load_data():

    global SPECIAL_TABLE, SPECIAL_OPTIONS
    global MEAT_TABLE, POWER_TABLE, OTHER_TABLE

    print("loading csv...")

    try:
        special_df = pd.read_csv(SPECIAL_CSV_URL)
        df = pd.read_csv(BASE_CSV_URL)

        new_special = {}
        new_options = []

        for _, row in special_df.iterrows():
            new_special[row["特殊能力"]] = int(row["経験点"])

        for name in new_special.keys():
            new_options.append(
                discord.SelectOption(label=name, value=name)
            )

        new_meat = {}
        new_power = {}
        new_other = {}

        for _, row in df.iterrows():
            ability = int(row["能力"])
            new_meat[ability] = int(row["ミート"])
            new_power[ability] = int(row["パワー"])
            new_other[ability] = int(row["その他"])

        # 成功時のみ反映（重要）
        SPECIAL_TABLE = new_special
        SPECIAL_OPTIONS = new_options
        MEAT_TABLE = new_meat
        POWER_TABLE = new_power
        OTHER_TABLE = new_other

        print("csv updated successfully")

    except Exception as e:
        print("csv update failed:", e)

# =========================
# 定期更新（5分）
# =========================

async def update_loop():

    await bot.wait_until_ready()

    while not bot.is_closed():
        load_data()
        await asyncio.sleep(300)

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

    # 他人操作防止
    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "これはあなた専用です",
                ephemeral=True
            )
            return False

        if self.finished:
            await interaction.response.send_message(
                "この計算は終了しています",
                ephemeral=True
            )
            return False

        return True

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_skills = self.select.values
        await interaction.response.defer()

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
            "入力形式エラー",
            ephemeral=True
        )

# =========================
# 起動
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    # 初回ロード
    load_data()

    # 5分更新開始
    bot.loop.create_task(update_loop())

print("starting bot...")

bot.run(TOKEN)