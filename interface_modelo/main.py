import streamlit as st
import os
import re

from normalizanome import normalizar_arquivos_na_pasta
from importdocdatastore import importDocsDataStore
from processastorage import uploadFile
from chatvertex import generate
from buscar_documentos import buscar_documentos_relevantes
from processastorage import gerar_url_assinada

def normalizar_nome_arquivo(nome_arquivo: str) -> str:
    nome_arquivo = nome_arquivo.replace(" ", "_")
    nome_arquivo = re.sub(r'[^a-zA-Z0-9_]', '', nome_arquivo)
    return nome_arquivo

def upload_pdf():
    st.sidebar.header("📄 Upload de Documento")  # Título visual aprimorado no sidebar

    uploaded_file = st.sidebar.file_uploader("Faça o upload de um arquivo PDF (Máximo 30MB)", type=["pdf"])
    if uploaded_file is not None:
        if uploaded_file.size > 30 * 1024 * 1024:
            st.error("O arquivo é maior que 30MB. Por favor, envie um arquivo menor.")
        else:
            os.makedirs("downloads", exist_ok=True)

            nome_seguro = normalizar_nome_arquivo(uploaded_file.name)
            save_path = os.path.join("downloads", nome_seguro)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            normalizar_arquivos_na_pasta('downloads')
            uploadFile()

            st.success("Arquivo enviado para o Bucket!")
            st.warning("Clique no botão abaixo para indexar os arquivos novamente.")

            if st.button("Indexar Arquivos"):
                importDocsDataStore()
                st.success("Indexação iniciada. Este processo pode demorar até 1 hora.")
                st.info("Você pode continuar usando o sistema enquanto a indexação ocorre.")

            return save_path
    return None

def main(authenticator):
    try:
        authenticator.login()
    except st.authenticator.LoginError as e:
        st.error(e)

    if st.session_state['authentication_status']:
        st.title("Análise de Documentos")

        # Inicializa o histórico de mensagens
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        with st.sidebar:
            st.header("Upload de Documento")
            caminho_arquivo = upload_pdf()

        # Exibe o histórico de mensagens anteriores
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # --- Input do usuário ---
        if prompt := st.chat_input("Digite sua pergunta"):
            # Adiciona mensagem do usuário
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Resposta da IA
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                try:
                    prompt = prompt.strip().strip('"').strip("'")
                    resposta_ia = generate(prompt)
                    resposta_ia = re.split(r'\*\*Documentos relacionados\*\*.*', resposta_ia, flags=re.IGNORECASE)[0].strip()
                    documentos = buscar_documentos_relevantes(prompt)

                    links_formatados = []

                    for doc_path in documentos:
                        try:
                            nome_arquivo = os.path.basename(doc_path)
                            url = gerar_url_assinada(doc_path)
                            links_formatados.append(f"- [{nome_arquivo}]({url})")
                        except Exception as e:
                            continue

                    if links_formatados:
                        documentos_md = "\n\n**Documentos relacionados:**\n" + "\n".join(links_formatados)
                    else:
                        documentos_md = "\n\n_Nenhum documento relacionado encontrado._"

                    full_response = resposta_ia + documentos_md

                except Exception as e:
                    full_response = f"Ocorreu um erro ao gerar a resposta: {e}"
                    st.error(full_response)

                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    elif st.session_state['authentication_status'] is False:
        st.error('Usuário ou senha inválidos')
    elif st.session_state['authentication_status'] is None:
        st.warning('Por favor, insira seu usuário e senha')
