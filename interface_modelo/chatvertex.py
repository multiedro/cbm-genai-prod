import streamlit as st
from google import genai
from google.genai import types
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

GOOGLE_APPLICATION_CREDENTIALS = './chave_collavini.json'

try:
    credentials, project = default()
except DefaultCredentialsError:
    st.error("Erro: Credenciais não encontradas. Verifique se configurou corretamente.")
    st.stop()



def generate(text):
    client = genai.Client(
        vertexai=True,
        project="collavini-genai-prod",
        location="global",
    )

    # Instrução fixa para o modelo
    si_text1 = """Você é um assistente jurídico inteligente. Responda perguntas com base no conteúdo dos documentos disponíveis no Data Store, utilizando linguagem técnica e precisa.

    Muito importante:
    - NÃO mencione arquivos, nomes de documentos, links ou caminhos.
    - NÃO adicione seções chamadas "Documentos relacionados", "Links", ou algo semelhante.
    - NÃO tente sugerir quais documentos consultar.
    - Foque apenas em responder a pergunta com base no conteúdo, sem fazer referência à origem.

    A apresentação de documentos será feita exclusivamente pelo sistema fora da sua resposta."""

    model = "gemini-2.5-flash"
    
    # Construindo o contexto da conversa a partir do histórico
    contents = []
    for message in st.session_state.messages:
        role = "user" if message["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]))

    # Adiciona a pergunta atual
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=text)]))

    tools = [
        types.Tool(retrieval=types.Retrieval(vertex_ai_search=types.VertexAISearch(
            datastore="projects/1050374636899/locations/global/collections/default_collection/dataStores/ds-collavini-pdfs-mais-importantes_1749661823675"
        )))
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=0.5, #anterior era 0.2
        top_p=0.95,
        max_output_tokens=65535,
        response_modalities=["TEXT"],
        tools=tools,
        system_instruction=[types.Part.from_text(text=si_text1)],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text
    else:
        return "Resposta não encontrada."