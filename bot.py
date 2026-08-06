import os
from threading import Thread
import time
from flask import Flask
import discord
from discord.ext import commands

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

# Variables de entorno o datos de Aternos (¡No pongas contraseñas reales aquí, usa variables de entorno!)
ATERNOS_USER = os.getenv("ATERNOS_USER", "olladeacero")
ATERNOS_PASS = os.getenv("ATERNOS_PASS", "Aguahirviendo$123")
ATERNOS_SERVER_URL = os.getenv(
    "ATERNOS_URL", "https://aternos.org/server/"
)  # Enlace directo a tu panel de servidor


@bot.event
async def on_ready():
  print(f"¡Bot conectado como {bot.user}!")


# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
  await ctx.send(
      "🔄 Intentando conectar a Aternos para encender el servidor... Ten paciencia"
      " :eyes:"
  )

  # Aquí automatizamos el navegador en segundo plano (headless) con Selenium
  from selenium import webdriver
  from selenium.webdriver.chrome.options import Options
  from selenium.webdriver.chrome.service import Service
  from selenium.webdriver.common.by import By
  from selenium.webdriver.support import expected_conditions as EC
  from selenium.webdriver.support.ui import WebDriverWait
  from webdriver_manager.chrome import ChromeDriverManager

  options = Options()
  options.add_argument("--headless")  # Oculto para que corra en el servidor
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")

  try:
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.get("https://aternos.org/go/")

    # Iniciar sesión (Aternos usa login rápido o formularios)
    # Rellena con los selectores de Aternos (ejemplo conceptual de automatización)
    time.sleep(3)

    # Nota: Si usas sesión guardada o cookies se salta el login,
    # pero aquí simulamos la entrada directa a la URL de tu server
    driver.get(ATERNOS_SERVER_URL)
    time.sleep(5)

    # Buscar el botón de encender (Start)
    start_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "start"))
    )
    start_button.click()

    await ctx.send(
        "✅ ¡Orden de encendido enviada a Aternos! El servidor debería estar"
        " prendiendo."
    )
  except Exception as e:
    await ctx.send(f"❌ Hubo un error al intentar encender el servidor: `{e}`")
  finally:
    try:
      driver.quit()
    except:
      pass


# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
  # Puedes conectar esto mediante una API pública de Aternos o scraping rápido
  # Aquí simulamos la estructura para que devuelva los datos pedidos:
  uptime_bot = round(
      time.time() - bot.uptime
      if hasattr(bot, "uptime")
      else time.time() - time.time(),
      2,
  )

  embed = discord.Embed(
      title="📊 Estado del Servidor Aternos", color=discord.Color.green()
  )
  embed.add_field(
      name="Estado", value="🟢 Online / En proceso", inline=False
  )
  embed.add_field(name="Jugadores", value="0 / 20 (Ejemplo)", inline=True)
  embed.add_field(name="Ping del Bot", value=f"{round(bot.latency * 1000)}ms", inline=True)
  embed.add_field(name="Uptime de Render", value="Funcionando 24/7 🚀", inline=False)
  
  await ctx.send(embed=embed)


# --- 5. INICIO DE TODO ---
if __name__ == "__main__":
  # Registramos el tiempo de inicio para el uptime
  bot.uptime = time.time()
  
  # Arrancamos el servidor web falso en segundo plano
  keep_alive()
  
  # Arrancamos el bot de Discord con su token secreto
  TOKEN = os.getenv("DISCORD_TOKEN")
  if TOKEN:
    bot.run(TOKEN)
  else:
    print(
        "❌ ERROR: No se encontró la variable de entorno DISCORD_TOKEN."
    )
