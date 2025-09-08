# Use uma imagem Python oficial como base
FROM python:3.11-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Copie o arquivo de requisitos para o diretório de trabalho
COPY requirements.txt .

# Instale as dependências necessárias
RUN pip install --no-cache-dir -r requirements.txt

# Copie todo o conteúdo da sua aplicação para o container
COPY . .

# Exponha a porta que o Streamlit usa por padrão
EXPOSE 8501

# Define o ponto de entrada para o Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.enableCORS=false"]
