import os
import re
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. SERVIDOR WEB 24/7 ---
app = Flask("")


@app.route("/")
def home():
  return "¡El bot de BelmoSMP está activo y súper ligero!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  t = Thread(target=run_web)
  t.start()


# --- 2. CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ATERNOS_SESSION = os.getenv("ATERNOS_SESSION")
MINECRAFT_IP = os.getenv("MINECRAFT_IP", "tu_servidor.aternos.me")
BOT_START_TIME = time.time()


@bot.event
async def on_ready():
  print(f"¡Bot conectado exitosamente como {bot.user}!")


# --- 3. COMANDO: !encender (Ultra ligero via API - ~30MB RAM) ---
@bot.command(name="encender")
async def encender(ctx):
  await ctx.send(
      f"🌱 Dale **{ctx.author.name}**, enviando orden rápida a Aternos para"
      " prender **BelmoSMP**... ⚡"
  )

  if not ATERNOS_SESSION:
    await ctx.send(
        "❌ Uy, falta la cookie de sesión (`ATERNOS_SESSION`) en la"
        " configuración de Render."
    )
    return

  try:
    # Configurar sesión HTTP rápida y ligera
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0)"
            " Gecko/20100101 Firefox/123.0"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })

    # Inyectar cookies de Aternos
    for item in ATERNOS_SESSION.split(";"):
      if "=" in item:
        name, val = item.strip().split("=", 1)
        session.cookies.set(name, val, domain=".aternos.org")

    # Step 1: Obtener la página del panel para extraer el Token SEC de Aternos
    panel_res = session.get("https://aternos.org/server/", timeout=10)

    # Buscar el token 'SEC' en el HTML del panel
    sec_match = re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text) or \
                re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', panel_res.text) or \
                re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text)

    if not sec_match:
      await ctx.send(
          "⚠️ No pude obtener el token de inicio de Aternos. Es muy posible"
          " que la cookie de sesión `ATERNOS_SESSION` haya caducado.\n👉 Prueba"
          " actualizar la variable `ATERNOS_SESSION` en Render copiando la"
          " nueva cookie desde tu navegador."
      )
      return

    sec_token = sec_match.group(1)

    # Step 2: Enviar la petición de encendido directamente
    start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
    start_res = session.get(start_url, timeout=10)

    if start_res.status_code == 200:
      resp_json = start_res.json()
      if resp_json.get("success"):
        await ctx.send(
            "🚀 **¡Listo!** Enviada la orden de encendido para **BelmoSMP**."
            " En un ratito ya pueden entrar a jugar 🎮"
        )
      else:
        error_msg = resp_json.get("error", "Desconocido")
        await ctx.send(
            f"⚠️ Aternos respondió pero no pudo iniciar. Razón: `{error_msg}`"
        )
    else:
      await ctx.send(
          f"⚠️ Aternos respondió con código HTTP `{start_res.status_code}`."
      )

  except Exception as e:
    await ctx.send(f"❌ Ocurrió un detalle al intentar conectar con Aternos:\n`{e}`")


# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
  await ctx.send("🔎 Revisando cómo está **BelmoSMP**... 📡")

  uptime_seconds = int(time.time() - BOT_START_TIME)
  hours, remainder = divmod(uptime_seconds, 3600)
  minutes, seconds = divmod(remainder, 60)
  uptime_str = f"{hours}h {minutes}m {seconds}s"

  is_online = False
  online_players = 0
  max_players = 0
  ping = "N/A"
  version = "Desconocida"

  try:
    res = requests.get(
        f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_IP}", timeout=8
    ).json()
    if res.get("online"):
      is_online = True
      online_players = res["players"]["online"]
      max_players = res["players"]["max"]
      ping = res.get("roundTripLatency", "N/A")
      version = res.get("version", {}).get("name_clean", "Desconocida")
  except Exception:
    try:
      res = requests.get(
          f"https://api.mcsrvstat.us/2/{MINECRAFT_IP}", timeout=8
      ).json()
      if res.get("online"):
        is_online = True
        online_players = res["players"]["online"]
        max_players = res["players"]["max"]
        version = res.get("version", "Desconocida")
    except Exception:
      pass

  if is_online:
    embed = discord.Embed(
        title="🎮 BelmoSMP está Online",
        description=(
            f"¡El servidor ya está listo! Pueden conectarse a `{MINECRAFT_IP}`"
            " ⚔️"
        ),
        color=discord.Color.green(),
    )
    embed.add_field(
        name="👥 Jugadores",
        value=f"**{online_players}/{max_players}**",
        inline=True,
    )
    embed.add_field(name="⚡ Ping MC", value=f"**{ping} ms**", inline=True)
    embed.add_field(
        name="📶 Ping Bot",
        value=f"**{round(bot.latency * 1000)} ms**",
        inline=True,
    )
    embed.add_field(name="📌 Versión", value=f"`{version}`", inline=False)
  else:
    embed = discord.Embed(
        title="😴 BelmoSMP está Apagado",
        description=(
            "💤 El servidor está durmiendo o cargando el mundo...\n\n👉 Pon"
            " **`!encender`** para prenderlo."
        ),
        color=discord.Color.red(),
    )
    embed.add_field(
        name="📶 Ping Bot",
        value=f"**{round(bot.latency * 1000)} ms**",
        inline=True,
    )

  embed.set_footer(
      text=f"Bot activo desde hace: {uptime_str} | IP: {MINECRAFT_IP}"
  )
  await ctx.send(embed=embed)


# --- 5. INICIO GENERAL ---
if __name__ == "__main__":
  keep_alive()
  TOKEN = os.getenv("DISCORD_TOKEN")
  if TOKEN:
    bot.run(TOKEN)
  else:
    print("❌ ERROR: Falta la variable DISCORD_TOKEN en el entorno.")
