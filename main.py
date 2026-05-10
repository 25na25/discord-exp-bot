import pandas as pd
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

# =========================
# 特殊能力テーブル読み込み
# =========================

SPECIAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=1840905945&single=true&output=csv"

special_df = pd.read_csv(SPECIAL_CSV_URL)

SPECIAL_TABLE = {}
SPECIAL_OPTIONS = []

for _, row in special_df.iterrows():

    skill_name = row["特殊能力"]
    exp = int(row["経験点"])

    SPECIAL_TABLE[skill_name] = exp

for skill_name in SPECIAL_TABLE.keys():

    SPECIAL_OPTIONS.append(
        discord.SelectOption(
            label=skill_name,
            value=skill_name
        )
    )

# =========================
# 基礎能力テーブル読み込み
# =========================

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=0&single=true&output=csv"

df = pd.read_csv(CSV_URL)

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

    def __init__(
        self,
        meat,
        power,
        run,
        defense,
        skill,
        mental
    ):

        super().__init__(timeout=300)

        self.meat = meat
        self.power = power
        self.run = run
        self.defense = defense
        self.skill = skill
        self.mental = mental

        self.selected_skills = []
        self.finished = False

        # プルダウン
        self.select = Select(
            placeholder="特殊能力を選択",
            min_values=0,
            max_values=min(len(SPECIAL_OPTIONS), 25),
            options=SPECIAL_OPTIONS
        )

        self.select.callback = self.select_callback

        self.add_item(self.select)

        # ボタン
        self.button = Button(
            label="計算",
            style=discord.ButtonStyle.green
        )

        self.button.callback = self.button_callback

        self.add_item(self.button)

    # =========================
    # プルダウン選択時
    # =========================


    async def interaction_check(self, interaction):

        if self.finished:

            await interaction.response.send_message(
                "この計算はすでに完了しています。",
                ephemeral=True
            )

            return False

        return True

    async def select_callback(self, interaction):

        if self.finished:

            await interaction.response.send_message(
                "この計算はすでに完了しています。",
                ephemeral=True
            )

            return

        self.selected_skills = self.select.values

        await interaction.response.defer()

    # =========================
    # 計算ボタン
    # =========================

    async def button_callback(self, interaction):

        if self.finished:

            await interaction.response.send_message(
                "この計算はすでに完了しています。",
                ephemeral=True
            )

            return

        # =========================
        # 基礎能力経験点
        # =========================

        meat_exp = MEAT_TABLE.get(self.meat, 0)
        power_exp = POWER_TABLE.get(self.power, 0)

        run_exp = OTHER_TABLE.get(self.run, 0)
        defense_exp = OTHER_TABLE.get(self.defense, 0)
        skill_exp = OTHER_TABLE.get(self.skill, 0)
        mental_exp = OTHER_TABLE.get(self.mental, 0)

        base_total = (
            meat_exp
            + power_exp
            + run_exp
            + defense_exp
            + skill_exp
            + mental_exp
        )

        # =========================
        # 特殊能力経験点
        # =========================

        special_total = 0
        special_text = ""

        for s in self.selected_skills:

            exp_value = SPECIAL_TABLE.get(s, 0)

            special_total += exp_value

            special_text += f"{s} : {exp_value}\n"

        # =========================
        # 総経験点
        # =========================

        total = base_total + special_total

        # =========================
        # Embed
        # =========================

        embed = discord.Embed(
            title="野手経験点計算結果",
            color=0x2ecc71
        )

        embed.add_field(
            name="能力値",
            value=(
                f"{self.meat}-{self.power}-{self.run}-{self.defense}-{self.skill}-{self.mental}"
            ),
            inline=False
        )

        embed.add_field(
            name="基礎能力",
            value=f"{base_total}",
            inline=False
        )

        if special_text != "":

            embed.add_field(
                name="特殊能力",
                value=(
                    special_text
                    + f"特殊能力計 : {special_total}"
                ),
                inline=False
            )

        embed.add_field(
            name="総経験点",
            value=f"{total}",
            inline=False
        )

        # =========================
        # UI無効化
        # =========================

        self.select.disabled = True

        self.button.disabled = True
        self.button.label = "計算済"
        self.button.style = discord.ButtonStyle.gray

        self.finished = True

        # =========================
        # UI更新
        # =========================

        await interaction.response.edit_message(
            content="✅ 計算完了",
            view=self
        )

        # =========================
        # 結果送信
        # =========================

        await interaction.followup.send(
            embed=embed
        )

# =========================
# Bot
# =========================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():

    await bot.tree.sync()

    print(f"{bot.user} でログインしました")

# =========================
# Slash Command
# =========================

@bot.tree.command(
    name="exp",
    description="野手経験点を計算します"
)

@app_commands.describe(
    values="ミート パワー 走力 守備 小技 精神"
)

async def exp(
    interaction: discord.Interaction,
    values: str
):

    try:

        meat, power, run, defense, skill, mental = map(
            int,
            values.split()
        )

        view = SpecialSkillView(
            meat,
            power,
            run,
            defense,
            skill,
            mental
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

bot.run(TOKEN)