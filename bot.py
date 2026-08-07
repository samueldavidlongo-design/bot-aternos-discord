import os
import re
import time
import urllib.parse
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. MANTENER VIVO EN RENDER (24/7) ---
app = Flask("")

@app.route("/")
def home():
    return "¡BelmoSMP Bot activo!"

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

BOT_START_TIME = time.time()

# --- 3. MOTOR MANUAL DE ATERNOS ---
class ManualAternosClient:
    def __init__(self):
        self.scrape_token = (
            os.getenv("SCRAPER_API_KEY") or 
            os.getenv("scrape_api_key") or 
            "9b8f9cb65f804598be72dd323213327559006dbca70"
        ).strip()
        self.user = os.getenv("ATERNOS_USER")
        self.password = os.getenv("ATERNOS_PASSWORD")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        })

    def request_scrapedo(self, target_url, method="GET", data=None, render_js=True):
        """Petición genérica pasando por Scrape.do manteniendo la sesión"""
        params = {
            'token': self.scrape_token,
            'url': target_url,
            'super': 'true'
        }
        if render_js:
            params['render'] = 'true'

        # Preparar headers incluyendo cookies actuales de la sesión
        headers = {}
        cookie_header_str = "; ".join([f"{k}={v}" for k, v in self.session.cookies.get_dict().items()])
        if cookie_header_str:
            headers['Cookie'] = cookie_header_str

        if method == "POST" and data:
            # Scrape.do acepta POST si se envían los datos
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            res = requests.post('https://api.scrape.do', params=params, headers=headers, data=data, timeout=45)
        else:
            res = requests.get('https://api.scrape.do', params=params, headers=headers, timeout=45)

        # Guardar cookies que devuelva la respuesta
        if res.cookies:
            self.session.cookies.update(res.cookies)

        return res

    def login_y_obtener_token(self):
        """1. Obtiene la página de login, extrae SEC/CSRF y envía credenciales manualmente."""
        if not self.user or not self.password:
            return None, "Faltan las variables `ATERNOS_USER` y `ATERNOS_PASSWORD` en Render."

        # Paso A: Obtener la página del panel (o redirección a login)
        panel_res = self.request_scrapedo("https://aternos.org/server/", render_js=True)
        if panel_res.status_code != 200:
            return None, f"Error HTTP {panel_res.status_code} al conectar con Aternos."

        html = panel_res.text

        # Intentar extraer TOKEN directamente si la sesión previa servía
        sec_token = self._extraer_token(html)
        if sec_token:
            return sec_token, None

        # Paso B: Si no hay token, significa que no estamos logueados. Hacer POST a /go/
        payload = {
            'user': self.user,
            'password': self.password
        }

        login_res = self.request_scrapedo("https://aternos.org/go/", method="POST", data=payload, render_js=True)
        
        # Paso C: Cargar de nuevo el panel para obtener el token AJAX tras el login
        panel_after_login = self.request_scrapedo("https://aternos.org/server/", render_js=True)
        sec_token = self._extraer_token(panel_after_login.text)

        if sec_token:
            return sec_token, None
        else:
            if "login" in panel_after_login.text.lower():
                return None, "Aternos rechazó el usuario o la contraseña provistos."
            return None, "No se pudo extraer el token AJAX tras el intento de inicio de sesión."

    def _extraer_token(self, html_text):
        """Expresiones regulares para encontrar el token dinámico de Aternos"""
        match = (
            re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', html_text) or
            re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', html_text) or
            re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', html_text) or
            re.search(r'head\s*=\s*["\']([^"\']+)["\']', html_text)
        )
        return match.group(1) if match else None

    def encender_servidor(self, sec_token):
        """Manda la petición directa al endpoint de start con el token extraído"""
        start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
        start_res = self.request_scrapedo(start_url, render_js=False)
        return start_res

@bot.event
async def on_ready():
    print(f"🤖 Bot encendido correctamente como: {bot.user}")

# --- 4. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"Entendido **{ctx.author.display_name}**, procesando credenciales e iniciando **BelmoSMP**... ⚡")

    client = ManualAternosClient()
    sec_token, err = client.login_y_obtener_token()

    if err:
        await ctx.send(f"❌ **[Error de Autenticación]:** `{err}`")
        return

    # Intentar mandar la orden de encendido con el token obtenido
    start_res = client.encender_servidor(sec_token)

    if start_res.status_code == 200:
        try:
            resp_json = start_res.json()
            if resp_json.get("success"):
                await ctx.send("🚀 **¡Listo! Servidor mandado a encender.** En unos minutos BelmoSMP estará listo para jugar. 🎮")
            else:
                msg = resp_json.get("error", "Desconocido")
                await ctx.send(f"⚠️ Aternos respondió pero no inició: `{msg}`")
        except Exception:
            await ctx.send("✅ ¡Orden enviada a Aternos! Revisa con `!status` en un momento.")
    else:
        await ctx.send(f"⚠️ **[Debug Error HTTP {start_res.status_code}]:** Falló la petición AJAX de inicio.")

# --- 5. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Consultando el estado de **BelmoSMP**...")

    minecraft_ip = os.getenv("MINECRAFT_IP", "belmosmp.aternos.me")
    
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    is_online = False
    online_players = 0
    max_players = 0
    version = "Desconocida"

    try:
        res = requests.get(f"https://api.mcsrvstat.us/3/{minecraft_ip}", timeout=6).json()
        if res.get("online") is True:
            is_online = True
            online_players = res.get("players", {}).get("online", 0)
            max_players = res.get("players", {}).get("max", 0)
            version = res.get("version", "Java")
    except Exception:
        is_online = False

    if is_online:
        embed = discord.Embed(
            title="🎮 ¡BelmoSMP está Online!",
            description=f"¡Servidor listo! IP: `{minecraft_ip}` ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=True)
    else:
        embed = discord.Embed(
            title="😴 BelmoSMP está Apagado",
            description="El servidor se encuentra offline.\n\n👉 Escribe **`!encender`** para iniciarlo.",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"Bot activo desde hace: {uptime_str} | IP: {minecraft_ip}")
    await ctx.send(embed=embed)

# --- 6. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta DISCORD_TOKEN.")
