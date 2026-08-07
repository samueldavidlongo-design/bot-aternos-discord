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

# --- 1. MANTENER VIVO ---
app = Flask("")
@app.route("/")
def home(): return "¡Zundabot Activo y listo! 🟢🌱"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=run_web, daemon=True).start()

# --- 2. CONFIGURACIÓN ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
ZUNDA_GREEN = discord.Color.from_rgb(120, 210, 110)

# --- HELPER: PROXIES VERIFICADOS ---
def obtener_proxies_funcionales():
    urls = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=anonymous",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    ]
    candidatos = set()
    for url in urls:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                for line in res.text.split("\n"):
                    if ":" in line: candidatos.add(line.strip())
        except: continue
    
    lista = list(candidatos)
    random.shuffle(lista)
    return lista[:10] # Top 10 para probar

# --- 3. NAVEGACIÓN ---
async def encender_aternos_playwright(status_callback):
    session = os.getenv("ATERNOS_SESSION")
    server_id = os.getenv("ATERNOS_SERVER_ID", "TG467pziBQ20JxmN")
    proxies = obtener_proxies_funcionales()
    proxies.insert(0, None) # Primero conexión directa

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--single-process", "--disable-gpu"])
        
        for i, proxy in enumerate(proxies):
            await status_callback(f"🌿 Ruta [{i+1}/11] usando: {'Conexión Directa' if not proxy else proxy}")
            context = None
            try:
                launch_opts = {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
                if proxy: launch_opts["proxy"] = {"server": f"http://{proxy}"}
                
                context = await browser.new_context(**launch_opts)
                await context.add_cookies([{"name": "ATERNOS_SESSION", "value": session, "domain": ".aternos.org", "path": "/"}])
                page = await context.new_page()

                await page.goto("https://aternos.org/servers/", timeout=20000)
                # Espera orgánica
                await asyncio.sleep(5)
                
                await page.goto(f"https://aternos.org/server/{server_id}/", timeout=20000)
                await asyncio.sleep(3)

                start_btn = await page.query_selector("#start")
                if start_btn:
                    await start_btn.click()
                    await asyncio.sleep(1)
                    confirm = await page.query_selector(".btn-confirm")
                    if confirm: await confirm.click()
                    await browser.close()
                    return True, "🚀 ¡Éxito! BelmoSMP está encendiendo. 🟢🌱"
                
                await context.close()
            except:
                if context: await context.close()
                continue
        
        await browser.close()
        return False, "🍂 Ninguna ruta funcionó. ¡Intenta de nuevo más tarde! ❌"

# --- 4. COMANDOS ---
@bot.command()
async def encender(ctx):
    msg = await ctx.send("🌱 **[Zundabot]** Iniciando ciclo de 10 rutas... 🍃")
    succ, res = await encender_aternos_playwright(lambda txt: asyncio.run_coroutine_threadsafe(msg.edit(content=f"🌱 {txt}"), loop=bot.loop))
    await msg.edit(content=f"{'🟢' if succ else '❌'} **{res}**")

@bot.run(os.getenv("DISCORD_TOKEN"))
