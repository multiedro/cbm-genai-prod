FROM apache/beam_python3.11_sdk:2.65.0

WORKDIR /opt/apache/beam/user_code/

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    sqlite3 \
    build-essential \
    python3-dev \
    fonts-dejavu-core \
    libreoffice \
    default-jre \
    fonts-wqy-zenhei \
    gnupg \
    curl \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY formats_converter.py /opt/apache/beam/user_code/

RUN chmod +x /opt/apache/beam/user_code/formats_converter.py