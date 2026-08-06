import os

# --- 5. INICIO GENERAL ---
from threading import Thread
import time
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (TRUCO 24/7 PARA RENDER) ---
app = Flask("")


@app.route("/")
def home():
  return "¡El bot de Aternos está activo y despierto!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


# --- 2. CONFIGURACIÓN DEL BOT DE DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variables de Entorno
ATERNOS_SESSION = os.getenv("ATERNOS_SESSION")
# Si no la configuras en Render, por defecto usará la IP que pongas abajo
MINECRAFT_IP = os.getenv("MINECRAFT_IP", "tu_servidor.aternos.me")

# Guardamos el momento exacto en que enciende el bot para calcular el Uptime
BOT_START_TIME = time.time()


@bot.event
async def on_ready():
  print(f"¡Bot conectado como {bot.user}!")


# --- 3. COMANDO: !encender (Mediante Cookies) ---
@bot.command(name="encender")
async def encender(ctx):
  await ctx.send(
      f"🔄 **{ctx.author.name}**, enviando orden para encender el servidor"
      " Aternos... ⏳"
  )

  if not ATERNOS_SESSION:
    await ctx.send(
        "❌ Error: Falta configurar la variable de entorno `ATERNOS_SESSION`"
        " en Render."
    )
    return

  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Cookie": ATERNOS_SESSION,
        "Referer": "https://aternos.org/server/",
    }

    response = requests.get(
        "https://aternos.org/panel/ajax/start.php", headers=headers
    )

    if response.status_code == 200:
      await ctx.send(
          f"✅ ¡Orden enviada con éxito por **{ctx.author.name}**! El servidor"
          " se está encendiendo 🚀\n*En un par de minutos estará disponible.*"
      )
    else:
      await ctx.send(
          "⚠️ Aternos respondió, pero hubo un problema (posiblemente la cookie"
          f" expiró). Código: `{response.status_code}`"
      )

  except Exception as e:
    await ctx.send(f"❌ Ocurrió un error de conexión:\n`{e}`")


# --- 4. COMANDO: !status (Información detallada de Minecraft) ---
@bot.command(name="status")
async def status(ctx):
  await ctx.send("🔎 Consultando con los satélites de Minecraft... 📡")

  # 1. Calcular Uptime del bot (Tiempo activo)
  uptime_seconds = int(time.time() - BOT_START_TIME)
  hours, remainder = divmod(uptime_seconds, 3600)
  minutes, seconds = divmod(remainder, 60)
  uptime_str = f"{hours}h {minutes}m {seconds}s"

  try:
    # 2. Consultar la API pública para saber el estado real del server
    api_url = f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_IP}"
    res = requests.get(api_url, timeout=5).json()

    if res.get("online"):
      # --- SERVIDOR ONLINE ---
      embed = discord.Embed(
          title=f"🎮 Servidor Online: {MINECRAFT_IP}",
          description=(
              "¡El mundo está abierto y listo para la aventura! ⚔️"
          ),
          color=discord.Color.green(),
      )

      # Jugadores y Ping
      online_players = res["players"]["online"]
      max_players = res["players"]["max"]
      ping = res.get("roundTripLatency", "N/A")
      version = res.get("version", {}).get("name_clean", "Desconocida")

      embed.add_field(
          name="👥 Jugadores",
          value=f"**{online_players}/{max_players}** en línea",
          inline=True,
      )
      embed.add_field(
          name="⚡ Ping Minecraft", value=f"**{ping} ms**", inline=True
      )
      embed.add_field(
          name="📶 Ping del Bot",
          value=f"**{round(bot.latency * 1000)} ms**",
          inline=True,
      )
      embed.add_field(
          name="📌 Versión", value=f"`{version}`", inline=False
      )

    else:
      # --- SERVIDOR OFFLINE ---
      embed = discord.Embed(
          title="😴 El servidor está fuera de línea",
          description=(
              "💤 *El mundo de Minecraft está durmiendo profundamente...*\n\n👉"
              " Escribe **`!encender`** para despabilar a Aternos y poner a"
              " marchar el server."
          ),
          color=discord.Color.red(),
      )
      embed.add_field(
          name="📶 Ping del Bot",
          value=f"**{round(bot.latency * 1000)} ms**",
          inline=True,
      )

    # Pie de página con el Uptime del servicio
    embed.set_footer(
        text=f"Bot activo en Render desde hace: {uptime_str} | IP:"
        f" {MINECRAFT_IP}"
    )
    await ctx.send(embed=embed)

  except Exception as e:
    await ctx.send(
        f"❌ Ocurrió un error al intentar consultar el estado: `{e}`"
    )


if __name__ == "__main__":
  keep_alive()
  TOKEN = os.getenv("DISCORD_TOKEN")
  if TOKEN:
    bot.run(TOKEN)
  else:
    print("❌ ERROR: No se encontró la variable de entorno DISCORD_TOKEN.")
