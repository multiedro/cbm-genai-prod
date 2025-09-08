from google.cloud import storage
from datetime import timedelta
import os
from google.oauth2 import service_account

# Define o caminho para o arquivo JSON da service account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = './chave_collavini.json'

# Função para gerar URL assinada
def gerar_url_assinada(caminho_arquivo, tempo_expiracao=240):
    # Extrai o nome do bucket e do arquivo
    caminho_split = caminho_arquivo.replace("gs://", "").split("/", 1)
    bucket_name = caminho_split[0]
    blob_name = caminho_split[1]  # NÃO codificar!

    # Inicializa o cliente do Cloud Storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Gera a URL assinada com tempo de expiração
    url_assinada = blob.generate_signed_url(expiration=timedelta(minutes=tempo_expiracao))
    return url_assinada


def uploadFile():

    # Caminho para o arquivo da chave da Service Account
    service_account_file = './chave_collavini.json'

    # Caminho local da pasta de onde os arquivos serão movidos
    local_directory = './downloads'

    # Nome do bucket de destino
    bucket_name = 'collavini-arquivos'

    # Cria o cliente de armazenamento autenticado usando a service account
    credentials = service_account.Credentials.from_service_account_file(service_account_file)
    client = storage.Client(credentials=credentials)

    # Acessa o bucket de destino
    bucket = client.bucket(bucket_name)

    # Itera sobre os arquivos na pasta local e faz upload para o bucket
    for filename in os.listdir(local_directory):
        local_file_path = os.path.join(local_directory, filename)
        
        if os.path.isfile(local_file_path):
            # Cria o blob no bucket (arquivo remoto)
            blob = bucket.blob(filename)
            
            # Faz o upload do arquivo para o bucket
            blob.upload_from_filename(local_file_path)
            
            # Deleta o arquivo local após o upload
            os.remove(local_file_path)
            print(f"Arquivo {filename} movido para o bucket e excluído localmente.")