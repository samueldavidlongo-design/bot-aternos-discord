import os
import time
import re
import asyncio
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as async_requests

# --- 1. MANTENER VIVO EN RENDER 24/7 ---
app = Flask("")

@app.route("/")
def home():
    return "¡Zundabot Activo con curl_cffi! 🟢🌱"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- 2. CONFIGURACIÓN DE ZUNDABOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_START_TIME = time.time()
ZUNDA_GREEN = discord.Color.from_rgb(120, 210, 110)

# --- 3. MOTOR DE ENCENDIDO CON CURL_CFFI ---
async def encender_aternos_curl(status_callback=None):
    session_cookie = os.getenv("ATERNOS_SESSION")
    server_id = os.getenv("ATERNOS_SERVER_ID", "TG467pziBQ20JxmN")

    async def reportar(texto):
        if status_callback:
            try:
                await status_callback(texto)
            except Exception:
                pass

    if not session_cookie:
        return False, "Falta la variable `ATERNOS_SESSION` en las variables de entorno de Render. ❌"

    await reportar("🟢 Conectando con Aternos mediante bypass TLS (curl_cffi)... 🍃")

    # Simulamos la huella TLS exacta de Chrome en Windows
    session = async_requests.AsyncSession(impersonate="chrome120")
    session.cookies.set("ATERNOS_SESSION", session_cookie, domain=".aternos.org")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://aternos.org/servers/",
    }

    try:
        url_panel = f"https://aternos.org/server/{server_id}/"
        await reportar("🌱 Solicitando acceso al panel del servidor...")

        response = await session.get(url_panel, headers=headers, timeout=20)

        if response.status_code == 403 or "Just a moment" in response.text or "Verificación de seguridad" in response.text:
            return False, "Cloudflare bloqueó el acceso. La sesión expiró o la IP fue restringida temporalmente."

        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar el token SEC que exige Aternos para ejecutar acciones AJAX
        sec_token = None
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "SEC" in script.string:
                match = re.search(r'SEC\s*=\s*["\']([^"\']+)["\']', script.string)
                if match:
                    sec_token = match.group(1)
                    break

        if not sec_token:
            # Si no hay token SEC pero sí cargó, verificamos si ya está encendido
            if "statuslabel-online" in response.text or "statuslabel-starting" in response.text:
                return True, "¡El servidor ya se encuentra en proceso de encendido o ya está en línea! 🟢"
            return False, "No se pudo extraer el token de seguridad (`SEC`) de la página. Verifica que `ATERNOS_SESSION` sea válida."

        # Extraer el ID único del servidor si cambia en el DOM
        server_sec_id = server_id
        sec_match = re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', response.text)
        if sec_match:
            server_sec_id = sec_match.group(1)

        await reportar("⚡ Enviando señal de encendido a Aternos...")

        # Enviar la petición POST directa de inicio
        ajax_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}&SEC={sec_token}"
        ajax_headers = headers.copy()
        ajax_headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Referer": url_panel
        })

        ajax_response = await session.get(ajax_url, headers=ajax_headers, timeout=15)
        res_json = ajax_response.json()

        if res_json.get("success"):
            return True, "¡Solicitud enviada con éxito! BelmoSMP se está encendiendo. 🟢🎮"
        else:
            error_msg = res_json.get("error", "Error desconocido devuelto por Aternos.")
            return False, f"Aternos no procesó la orden: `{error_msg}`"

    except Exception as e:
        return False, f"Error en la conexión con Aternos: `{str(e)}`"

@bot.event
async def on_ready():
    print(f"🤖 Zundabot encendido correctamente como: {bot.user} 🟢🌱")

# --- 4. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    msg = await ctx.send(f"🟢 **[Zundabot]** Entendido **{ctx.author.display_name}**, inicializando servidor... Por favor espera. 🍃")

    async def actualizar_mensaje(texto_nuevo):
        try:
            await msg.edit(content=f"🟢 **[Zundabot]** {texto_nuevo}")
        except Exception:
            pass

    success, result_message = await encender_aternos_curl(status_callback=actualizar_mensaje)

    if success:
        await msg.edit(content=f"🚀 **[Zundabot]** {result_message} 🍃")
    else:
        await msg.edit(content=f"❌ **[Zundabot Error]:** {result_message}")

# --- 5. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    msg = await ctx.send("🔎 **[Zundabot]** Consultando estado del servidor... Por favor espera. 🍃")

    minecraft_ip = os.getenv("MINECRAFT_IP", "belmosmp.aternos.me")
    
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    try:
        res = requests.get(f"https://api.mcsrvstat.us/3/{minecraft_ip}", timeout=7).json()
        
        is_online = res.get("online", False)
        
        if is_online:
            online_players = res.get("players", {}).get("online", 0)
            max_players = res.get("players", {}).get("max", 0)
            version = res.get("version", "Java Edition")
            
            player_list = res.get("players", {}).get("list", [])
            if player_list:
                players_formatted = ", ".join([p.get("name", "Jugador") for p in player_list])
            else:
                players_formatted = "Sin jugadores conectados actualmente."

            motd_raw = res.get("motd", {}).get("clean", ["¡Servidor BelmoSMP!"])
            motd_text = " ".join(motd_raw).strip() if motd_raw else "¡BelmoSMP Minecraft!"

            embed = discord.Embed(
                title="🟢 BelmoSMP está en línea",
                description=f"```{motd_text}```",
                color=ZUNDA_GREEN
            )
            embed.set_thumbnail(url="https://api.mcsrvstat.us/icon/" + minecraft_ip)
            embed.add_field(name="📌 Dirección IP", value=f"`{minecraft_ip}`", inline=True)
            embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
            embed.add_field(name="⚙️ Versión", value=f"`{version}`", inline=True)
            embed.add_field(name="🎮 Jugadores en línea", value=f"{players_formatted}", inline=False)
            embed.set_footer(text=f"Zundabot activo hace: {uptime_str} 🟢 | BelmoSMP", icon_url=bot.user.display_avatar.url)
            
            await msg.edit(content="✨ **El servidor está listo para jugar.** 🟢", embed=embed)

        else:
            embed = discord.Embed(
                title="🔴 BelmoSMP está apagado",
                description="El servidor se encuentra **offline** actualmente.\n\n👉 Puedes usar **`!encender`** para iniciarlo. 🍃",
                color=discord.Color.red()
            )
            embed.add_field(name="📌 Dirección IP", value=f"`{minecraft_ip}`", inline=True)
            embed.set_footer(text=f"Zundabot activo hace: {uptime_str} 🟢", icon_url=bot.user.display_avatar.url)
            
            await msg.edit(content="🔴 **Estado del servidor:**", embed=embed)

    except Exception as e:
        await msg.edit(content=f"⚠️ **Error al consultar el estado:** `{str(e)}`")

# --- 6. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta DISCORD_TOKEN.")
