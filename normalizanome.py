import os
import re

def normalizar_nome_arquivo(nome_arquivo: str) -> str:
    # Separa o nome do arquivo da extensão
    nome, extensao = os.path.splitext(nome_arquivo)
    
    # Converte o nome do arquivo para minúsculas
    nome = nome.lower()
    
    # Substitui os espaços por underscores no nome do arquivo
    nome = nome.replace(" ", "_")
    
    # Remove todos os caracteres especiais, mantendo apenas letras, números e underscores
    nome = re.sub(r'[^a-zA-Z0-9_]', '', nome)
    
    # Retorna o nome normalizado com a extensão intacta
    return nome + extensao

def normalizar_arquivos_na_pasta(pasta: str):
    # Verifica se a pasta existe
    if not os.path.exists(pasta):
        print(f"A pasta '{pasta}' não existe.")
        return
    
    # Percorre todos os arquivos na pasta
    for nome_arquivo in os.listdir(pasta):
        caminho_arquivo = os.path.join(pasta, nome_arquivo)
        
        # Verifica se é um arquivo (não uma pasta)
        if os.path.isfile(caminho_arquivo):
            # Normaliza o nome do arquivo
            nome_arquivo_normalizado = normalizar_nome_arquivo(nome_arquivo)
            
            # Verifica se o nome foi alterado
            if nome_arquivo != nome_arquivo_normalizado:
                # Cria o novo caminho com o nome normalizado
                caminho_arquivo_normalizado = os.path.join(pasta, nome_arquivo_normalizado)
                
                # Renomeia o arquivo
                os.rename(caminho_arquivo, caminho_arquivo_normalizado)
                print(f"Arquivo renomeado: {nome_arquivo} -> {nome_arquivo_normalizado}")