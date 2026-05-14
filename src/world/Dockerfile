# Usa uma imagem oficial do Python, versão leve
FROM python:3.10-slim

# Instala as dependências do sistema necessárias para o Pygame/SDL2
RUN apt-get update && apt-get install -y \
    python3-sdl2 \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    libportmidi-dev \
    libjpeg-dev \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia os requisitos e instala o Pygame
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código para o contêiner
COPY . .

# Comando para rodar o jogo
CMD ["python", "main.py"]