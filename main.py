import os
import threading
import pandas as pd
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
from flask import Flask

# =========================
# Flask（死活監視用）
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# =========================
# Bot初期設定
# =========================

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKENが設定されていません（RenderのEnvironment Variables確認）")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# =========================
# データ（起動時に読まない！）
# =========================

SPECIAL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=1840905945&single=true&output=csv"
BASE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdr67r8mLDyl_qeoKJF5qFNHV0CR969ayqHtBAaH9u-bmyIq7T9vuIy-A754_D59xo_95puCGHeo4d/pub?gid=0&single=true&output=csv"

SPECIAL_TABLE = {}
SPECIAL_OPTIONS = []

MEAT_TABLE = {}
POWER_TABLE = {}
OTHER_TABLE = {}


# =========================
# 安全ロード関数（ここが重要）
# =========================

def safe_load_csv(url: str):
    try:
        return pd.read_csv(url)
    except Exception as e:
        print(f"[CSV LOAD ERROR] {url} : {e}")
        return None


def load_data():
    global SPECIAL_TABLE, SPECIAL_OPTIONS
    global MEAT_TABLE, POWER_TABLE, OTHER_TABLE

    # ---- 特殊能力 ----
    df_special = safe_load_csv(SPECIAL_CSV_URL)
    if df_special is not None:
        SPECIAL_TABLE = {}
        SPECIAL_OPTIONS = []

        for _, row in df_special.iterrows():
            name = row["特殊能力"]
            exp = int(row["経験点"])
            SPECIAL_TABLE[name] = exp

        for name in SPECIAL_TABLE.keys():
            SPECIAL_OPTIONS.append(
                discord.SelectOption(label=name, value=name)
            )

    # ---- 基礎能力 ----
    df_base = safe_load_csv(BASE_CSV_URL)
    if df_base is not None:
        MEAT_TABLE = {}
        POWER_TABLE = {}
        OTHER_TABLE = {}

        for _, row in df_base.iterrows():
            ability = int(row["能力"])
            MEAT_TABLE[ability] = int(row["ミート"])
            POWER_TABLE[ability] = int(row["パワー"])
            OTHER_TABLE[ability] = int(row["その他"])


# =========================
# View
# =========================

class SpecialSkillView(View):

    def __init__(self, user_id: int, meat, power, run, defense, skill, mental):
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
            await interaction.response.send_message("これはあなたの計算ではありません", ephemeral=True)
            return False

        if self.finished:
            await interaction.response.send_message("すでに計算済みです", ephemeral=True)
            return False

        return True

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_skills = self.select.values
        await interaction.response.defer()

    async def button_callback(self, interaction: discord.Interaction):

        meat_exp = MEAT_TABLE.get(self.meat, 0)
        power_exp = POWER_TABLE.get(self.power, 0)
        run_exp = OTHER_TABLE.get(self.run, 0)
        defense_exp = OTHER_TABLE.get(self.defense, 0)
        skill_exp = OTHER_TABLE.get(self.skill, 0)
        mental_exp = OTHER_TABLE.get(self.mental, 0)

        base_total = (
            meat_exp + power_exp + run_exp +
            defense_exp + skill_exp + mental_exp
        )

        special_total = 0
        special_text = ""

        for s in self.selected_skills:
            val = SPECIAL_TABLE.get(s, 0)
            special_total += val
            special_text += f"{s} : {val}\n"

        total = base_total + special_total

        embed = discord.Embed(title="経験点計算結果", color=0x2ecc71)

        embed.add_field(
            name="能力値",
            value=f"{self.meat}-{self.power}-{self.run}-{self.defense}-{self.skill}-{self.mental}",
            inline=False
        )

        embed.add_field(name="基礎", value=str(base_total), inline=False)

        if special_text:
            embed.add_field(
                name="特殊能力",
                value=f"{special_text}合計:{special_total}",
                inline=False
            )

        embed.add_field(name="総計", value=str(total), inline=False)

        self.finished = True
        self.select.disabled = True
        self.button.disabled = True
        self.button.label = "完了"

        await interaction.response.edit_message(content="完了", view=self)
        await interaction.followup.send(embed=embed)


# =========================
# Bot起動
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # ★ここで初めてデータ読む（超重要）
    load_data()

    try:
        await bot.tree.sync()
    except Exception as e:
        print("sync error:", e)


@bot.tree.command(name="exp", description="経験点計算")
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

    except Exception as e:
        await interaction.response.send_message(f"エラー: {e}", ephemeral=True)


# =========================
# メイン起動
# =========================

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)