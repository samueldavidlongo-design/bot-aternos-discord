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

# Credenciales desde las Variables de Entorno de Render
ATERNOS_USER = os.getenv("ATERNOS_USER")
ATERNOS_PASS = os.getenv("ATERNOS_PASS")
ATERNOS_SERVER_URL = os.getenv(
    "ATERNOS_URL", "https://aternos.org/server/"
)  # Tu enlace directo al panel


@bot.event
async def on_ready():
  print(f"¡Bot conectado como {bot.user}!")


# --- 3. COMANDO: !encender (Público y optimizado para Aternos) ---
@bot.command(name="encender")
async def encender(ctx):
  await ctx.send(
      f"🔄 **{ctx.author.name}**, intentando conectar con Aternos para encender"
      " el servidor... Esto puede tardar unos segundos. ⏳"
  )

  from selenium import webdriver
  from selenium.webdriver.chrome.options import Options
  from selenium.webdriver.chrome.service import Service
  from selenium.webdriver.common.by import By
  from selenium.webdriver.support import expected_conditions as EC
  from selenium.webdriver.support.ui import WebDriverWait
  from webdriver_manager.chrome import ChromeDriverManager
  from webdriver_manager.core.os_manager import ChromeType

  options = Options()
  options.add_argument("--headless")  # Obligatorio para servidores en la nube
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--disable-gpu")
  options.add_argument("--window-size=1920,1080")
  # Añadimos un user-agent genérico para evitar que Aternos bloquee el navegador automatizado
  options.add_argument(
      "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  )

  driver = None
  try:
    # Inicializar Chromium compatible con Linux en Render
    driver = webdriver.Chrome(
        service=Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        ),
        options=options,
    )

    # 1. Ir a la página de login de Aternos
    driver.get("https://aternos.org/go/")
    time.sleep(3)

    # Si hay campos de texto para usuario y contraseña, los rellenamos automáticamente
    try:
      username_input = WebDriverWait(driver, 5).until(
          EC.presence_of_element_located((By.ID, "user"))
      )
      password_input = driver.find_element(By.ID, "password")
      login_button = driver.find_element(By.ID, "login")

      if ATERNOS_USER and ATERNOS_PASS:
        username_input.send_keys(ATERNOS_USER)
        password_input.send_keys(ATERNOS_PASS)
        login_button.click()
        time.sleep(5)  # Esperar a que procese el inicio de sesión
    except Exception:
      # Si ya venía con sesión guardada o cookies, continúa directo
      pass

    # 2. Entrar al panel del servidor específico
    driver.get(ATERNOS_SERVER_URL)
    
    # 3. Esperar y hacer clic en el botón de encender ("start")
    start_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "start"))
    )
    start_button.click()

    await ctx.send(
        f"✅ ¡Orden enviada con éxito por **{ctx.author.name}**! El servidor"
        " Aternos se está encendiendo. 🚀"
    )

  except Exception as e:
    await ctx.send(
        f"❌ Ocurrió un error al intentar encender el servidor:\n`{e}`"
    )
  finally:
    if driver:
      try:
        driver.quit()
      except:
        pass


# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
  embed = discord.Embed(
      title="📊 Estado del Servidor y Bot", color=discord.Color.green()
  )
  embed.add_field(
      name="Estado del Bot", value="🟢 Online 24/7 (Render)", inline=False
  )
  embed.add_field(
      name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True
  )
  embed.add_field(
      name="Uso", value="Usa `!encender` para prender el Aternos", inline=False
  )

  await ctx.send(embed=embed)


# --- 5. INICIO GENERAL ---
if __name__ == "__main__":
  # Arrancar servidor web para Flask (Truco de Render)
  keep_alive()

  # Arrancar el bot de Discord
  TOKEN = os.getenv("DISCORD_TOKEN")
  if TOKEN:
    bot.run(TOKEN)
  else:
    print("❌ ERROR: No se encontró la variable de entorno DISCORD_TOKEN.")
