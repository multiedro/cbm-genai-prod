# 📂 Visão Geral das Etapas

Este repositório contém duas etapas principais que utilizam tecnologias do Google Cloud para processamento e análise de documentos.

# ⚙️ Etapa 1: Conversor de Formatos de Arquivos com Apache Beam e Dataflow

Esta etapa, encontrada na pasta *conversor_formatos*, utiliza o Apache Beam para orquestrar um pipeline de processamento de dados em lote no Google Cloud Dataflow. A principal função do pipeline é monitorar uma pasta no Google Cloud Storage (GCS), converter diversos formatos de arquivo para o formato PDF e salvar os arquivos resultantes em outra pasta no mesmo bucket.

## 🏛️ Visão Geral da Arquitetura

O processo funciona da seguinte maneira:

O script Python `formats_converter.py` define um pipeline do Apache Beam.

Ao ser executado, o script submete o pipeline para o serviço do Google Cloud Dataflow.

O Dataflow provisiona instâncias de máquina virtual (workers) para executar as tarefas de conversão.

Cada worker utiliza uma imagem Docker customizada (Dockerfile), que contém todas as dependências necessárias (como LibreOffice e bibliotecas Python) para realizar as conversões.

O pipeline lê os arquivos de uma pasta de origem no GCS, distribui as tarefas de conversão entre os workers e, por fim, salva os PDFs gerados em uma pasta de destino.

## 📄 Descrição dos Arquivos

- `formats_converter.py`: Arquivo principal que contém toda a lógica do pipeline de dados com Apache Beam. Ele lista, filtra e processa arquivos do GCS, utilizando LibreOffice e bibliotecas Python para a conversão para PDF.

- `Dockerfile`: Define o ambiente de execução customizado para os workers do Dataflow, instalando o LibreOffice e outras dependências de sistema e Python.

- `requirements.txt`: Lista as bibliotecas Python necessárias para o pipeline de conversão, como apache-beam[gcp], Pillow, reportlab, etc.

## 🚀 Como Executar a Etapa

### Pré-requisitos

- Um projeto no Google Cloud com as APIs do Dataflow, Cloud Storage e Container Registry ativadas.

- Um bucket no Google Cloud Storage.

- O Google Cloud SDK (gcloud) instalado e autenticado.

- Docker instalado.

### Passos para Execução

- Configurar Variáveis: Atualize as variáveis globais em formats_converter.py (nome do bucket, pastas, ID do projeto, etc.).

- Construir e Enviar a Imagem Docker:

```
Autenticar o Docker com o gcloud
gcloud auth configure-docker

Construir a imagem Docker
docker build -t gcr.io/[YOUR_PROJECT_ID]/formats_converter:latest .

Enviar a imagem para o Google Container Registry
docker push gcr.io/[YOUR_PROJECT_ID]/formats_converter:latest
```
- Preparar o Ambiente no GCS: Crie as pastas de origem e destino no seu bucket e faça o upload dos arquivos a serem convertidos.

### Executar o Pipeline:

```python3 formats_converter.py```

O progresso do job pode ser acompanhado na interface do Dataflow no Console do Google Cloud.


# 💬 Etapa 2: Chatbot de Análise de Documentos com Streamlit e Vertex AI

Esta etapa, encontrada na pasta *interface_modelo*, consiste em uma aplicação web de chatbot construída com Streamlit. A aplicação permite que os usuários façam upload de documentos, que são então indexados no Vertex AI Search. Os usuários podem fazer perguntas em linguagem natural, e o chatbot utiliza um modelo generativo (Gemini) com a técnica de RAG (Retrieval-Augmented Generation) para responder com base no conteúdo dos documentos.

## 🏛️ Visão Geral da Arquitetura

- A interface do usuário é construída com Streamlit (`app.py`, `main.py`).

- Um sistema de autenticação (*streamlit-authenticator*) controla o acesso.

- Os usuários fazem upload de arquivos PDF através da interface. Os nomes dos arquivos são normalizados (`normalizanome.py`).

- Os arquivos são enviados para um bucket do Google Cloud Storage (`processastorage.py`).

- Um script (`importdocdatastore.py`) é acionado para indexar os novos documentos no Vertex AI Search (*Data Store*).

- Quando um usuário faz uma pergunta, a aplicação primeiro busca documentos relevantes no Data Store (`buscar_documentos.py`).

- A pergunta do usuário, juntamente com o conteúdo dos documentos relevantes, é enviada para um modelo Gemini (*Vertex AI*) para gerar uma resposta precisa e contextualizada (`chatvertex.py`).

- A resposta e os links para os documentos de origem são exibidos na interface do chat.

## 📄 Descrição dos Arquivos

- `app.py`: Ponto de entrada da aplicação Streamlit. Gerencia a autenticação de usuários, a navegação e a renderização das páginas.

- `main.py`: Contém a lógica principal da interface de chat, incluindo upload de arquivos e orquestração da busca e geração de respostas.

- `chatvertex.py`: Interage com a API do Vertex AI para gerar as respostas do chatbot utilizando o modelo Gemini e RAG.

- `buscar_documentos.py`: Utiliza o Vertex AI Search para encontrar os documentos mais relevantes para a pergunta do usuário.

- `importdocdatastore.py`: Inicia a indexação de documentos do GCS para um Data Store do Vertex AI Search.

- `processastorage.py`: Funções utilitárias para interagir com o GCS (upload, geração de URLs assinadas).

- `normalizanome.py`: Script auxiliar para padronizar nomes de arquivos antes do upload.

- `Dockerfile`: Define o ambiente para containerizar a aplicação Streamlit.

- `requirements.txt`: Lista todas as dependências Python para a aplicação.

- `config_credential.yaml`: Arquivo de configuração do streamlit-authenticator, armazenando os detalhes e senhas (hash) dos usuários.

## 🚀 Como Executar a Etapa

### Pré-requisitos

- Um projeto no Google Cloud com as APIs Vertex AI Search, Vertex AI e Cloud Storage ativadas.

- Um Data Store configurado no Vertex AI Search.

- Um arquivo de credenciais de Service Account (chave_collavini.json) no diretório raiz.

- Um arquivo de configuração de usuários (config_credential.yaml).

- Docker instalado.

### Passos para Execução

- *Configurar Variáveis:* Revise os scripts e atualize os IDs do projeto, Data Store e bucket do GCS conforme necessário.

- Construir e Executar o Contêiner Docker:

```
# Construir a imagem Docker
docker build -t cbm-adv:latest .

# Executar o contêiner
docker run -p 8080:8080 cbm-adv:latest
```

- *Acessar a Aplicação:* Abra seu navegador e acesse http://localhost:8080.

- *Uso:* Faça o login, realize o upload de documentos PDF pela barra lateral e comece a interagir com o chatbot.
