import os
import time
import asyncio
import random
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests
from playwright.async_api import async_playwright

# --- 1. MANTENER VIVO EN RENDER 24/7 ---
app = Flask("")

@app.route("/")
def home():
    return "¡Zundabot Activo y listo para la cosecha! 🟢🌱"

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

# --- HELPER: OBTENER PROXIES LIGEROS ---
def obtener_proxies_gratuitos():
    urls_fuente = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=anonymous,elite",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    ]
    
    proxies_encontrados = []
    for url in urls_fuente:
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                lineas = [line.strip() for line in res.text.split("\n") if line.strip() and ":" in line]
                proxies_encontrados.extend(lineas)
        except Exception:
            continue

    random.shuffle(proxies_encontrados)
    return proxies_encontrados[:6] # Reducido a 6 para no consumir memoria innecesaria

# --- 3. NAVEGACIÓN PLAYWRIGHT ULTRA-OPTIMIZADA (512MB RAM FRIENDLY) ---
async def encender_aternos_playwright(status_callback=None):
    session_cookie = os.getenv("ATERNOS_SESSION")
    user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    server_id = os.getenv("ATERNOS_SERVER_ID", "TG467pziBQ20JxmN")

    async def reportar(texto):
        if status_callback:
            try:
                await status_callback(texto)
            except Exception:
                pass

    if not session_cookie:
        return False, "⚠️ ¡Ups! Falta configurar la variable `ATERNOS_SESSION` en Render. 🌱❌"

    await reportar("🌱 Preparando semillas y configurando la Conexión Estelar Directa... 🍃")
    
    lista_proxies = obtener_proxies_gratuitos()
    lista_proxies.insert(0, None) # Conexión directa primero

    async with async_playwright() as p:
        # Uso estricto de --single-process para ahorrar RAM drásticamente
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--single-process",
                "--disable-gpu"
            ]
        )

        for i, proxy in enumerate(lista_proxies):
            tipo_conexion = "Conexión Directa Estelar 🌟" if not proxy else f"Proxy `{proxy}`"
            await reportar(f"🌿 Intentando ruta [{i+1}/{len(lista_proxies)}] con {tipo_conexion}...")

            context = None
            try:
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1280, "height": 720}
                )
                
                await context.add_cookies([{
                    "name": "ATERNOS_SESSION",
                    "value": session_cookie,
                    "domain": ".aternos.org",
                    "path": "/"
                }])

                page = await context.new_page()

                # Navegar a la lista de servidores
                await page.goto("https://aternos.org/servers/", wait_until="domcontentloaded", timeout=25000)

                # Bucle de espera ligero (aprox 25-30s) para pasar Cloudflare de forma fluida
                for _ in range(12):
                    if "servers" in page.url or "server" in page.url:
                        break
                    try:
                        await page.mouse.move(random.randint(200, 700), random.randint(200, 500), steps=5)
                    except Exception:
                        pass
                    await asyncio.sleep(2.5)

                # Navegar directamente al servidor
                await page.goto(f"https://aternos.org/server/{server_id}/", timeout=20000)
                await asyncio.sleep(3)

                # Verificar y hacer clic en el botón de encendido si está disponible
                start_btn = await page.query_selector("#start")
                if start_btn:
                    await start_btn.click()
                    await asyncio.sleep(1.5)
                    
                    # Confirmar si aparece el diálogo
                    confirm_btn = await page.query_selector(".btn-confirm, #confirm")
                    if confirm_btn:
                        await confirm_btn.click()
                    
                    await context.close()
                    await browser.close()
                    return True, "🚀 ¡Señal enviada con éxito! BelmoSMP está despertando. 🟢🌱🎮"

                await context.close()

            except Exception:
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass
                continue

        await browser.close()
        return False, "🍂 Memoria limitada o bloqueo persistente. ¡Vuelve a probar con `!encender`!"

@bot.event
async def on_ready():
    print(f"🤖 Zundabot encendido y conectado correctamente como: {bot.user} 🟢🌱")

# --- 4. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    msg = await ctx.send(f"🌱 **[Zundabot]** ¡Entendido **{ctx.author.display_name}**! Zundamon abrió la ruta optimizada para 512MB... 🍃💚")

    async def actualizar_mensaje(texto_nuevo):
        try:
            await msg.edit(content=f"🌱 **[Zundabot]** {texto_nuevo}")
        except Exception:
            pass

    success, result_message = await encender_aternos_playwright(status_callback=actualizar_mensaje)

    if success:
        await msg.edit(content=f"🟢 **[Zundabot Éxito]** {result_message} 🌿✨")
    else:
        await msg.edit(content=f"❌ **[Zundabot Brote Cortado]:** {result_message}")

# --- 5. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    msg = await ctx.send("🔍 **[Zundabot]** Inspeccionando el estado del jardín BelmoSMP... Un momento 🍃🌿")

    minecraft_ip = os.getenv("MINECRAFT_IP", "belmosmp.aternos.me")
    
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    try:
        res = requests.get(f"https://api.mcsrvstat.us/3/{minecraft_ip}", timeout=6).json()
        is_online = res.get("online", False)
        
        if is_online:
            online_players = res.get("players", {}).get("online", 0)
            max_players = res.get("players", {}).get("max", 0)
            version = res.get("version", "Java Edition")
            
            player_list = res.get("players", {}).get("list", [])
            players_formatted = ", ".join([p.get("name", "Jugador") for p in player_list]) if player_list else "Ningún aventurero conectado por ahora."

            motd_raw = res.get("motd", {}).get("clean", ["¡Servidor BelmoSMP!"])
            motd_text = " ".join(motd_raw).strip() if motd_raw else "¡BelmoSMP Minecraft!"

            embed = discord.Embed(
                title="🟢 ¡BelmoSMP está floreciendo (En Línea)!",
                description=f"```{motd_text}```",
                color=ZUNDA_GREEN
            )
            embed.set_thumbnail(url="https://api.mcsrvstat.us/icon/" + minecraft_ip)
            embed.add_field(name="📌 Dirección IP", value=f"`{minecraft_ip}`", inline=True)
            embed.add_field(name="👥 Aventureros", value=f"**{online_players}/{max_players}**", inline=True)
            embed.add_field(name="⚙️ Versión", value=f"`{version}`", inline=True)
            embed.add_field(name="🎮 Jugadores activos", value=f"{players_formatted}", inline=False)
            embed.set_footer(text=f"Zundabot floreciendo hace: {uptime_str} 🟢 | BelmoSMP 🍃", icon_url=bot.user.display_avatar.url)
            
            await msg.edit(content="✨ **¡El servidor está listo para cosechar victorias y jugar!** 🟢🌱", embed=embed)

        else:
            embed = discord.Embed(
                title="🔴 BelmoSMP está descansando (Apagado)",
                description="El servidor se encuentra **offline** en este momento.\n\n👉 Escribe **`!encender`** para que Zundamon despierte el servidor 🍃💚",
                color=discord.Color.from_rgb(220, 90, 90)
            )
            embed.add_field(name="📌 Dirección IP", value=f"`{minecraft_ip}`", inline=True)
            embed.set_footer(text=f"Zundabot activo hace: {uptime_str} 🟢", icon_url=bot.user.display_avatar.url)
            
            await msg.edit(content="🔴 **Estado del servidor:**", embed=embed)

    except Exception as e:
        await msg.edit(content=f"⚠️ **Error al consultar el jardín:** `{str(e)}`")

# --- 6. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta configurar DISCORD_TOKEN.")
