FROM python:3.10-slim

WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar los archivos del proyecto
COPY . .

EXPOSE 8080

CMD ["python", "bot.py"]
