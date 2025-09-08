import yaml
import streamlit as st
#from PIL import Image # Descomente para carregar a imagem
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from main import main as home_main
from streamlit_authenticator.utilities import (
    CredentialsError, LoginError, RegisterError, ResetError, UpdateError
)

st.set_page_config(layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ======== Funções utilitárias ========
def carregar_config():
    with open('./config_credential.yaml', 'r', encoding='utf-8') as file:
        return yaml.load(file, Loader=SafeLoader)

def salvar_config(config):
    with open('./config_credential.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False)

# ======== Páginas ========
def render_home():
    home_main(authenticator)


def render_criar_usuario(authenticator, config):
    try:
        email, username, name = authenticator.register_user()
        if email:
            st.success('Usuário registrado com sucesso!')
            salvar_config(config)  # Salvar após criação
    except RegisterError as e:
        st.error(e)


def render_resetar_senha(authenticator):
    try:
        if authenticator.reset_password(st.session_state['username']):
            st.success('Senha modificada com sucesso!')
            salvar_config(config)
    except (CredentialsError, ResetError) as e:
        st.error(e)


def render_atualizar_dados(authenticator):
    try:
        if authenticator.update_user_details(st.session_state['username']):
            st.success('Dados atualizados com sucesso!')
            salvar_config(config)
    except UpdateError as e:
        st.error(e)

def render_remover_usuario(config):
    st.subheader("Remover Usuário")

    try:
        # Lista todos os usuários, exceto o logado (admin atual)
        usuarios = list(config['credentials']['usernames'].keys())
        if st.session_state['username'] in usuarios:
            usuarios.remove(st.session_state['username'])

        if not usuarios:
            st.info("Nenhum outro usuário disponível para remover.")
            return

        usuario_selecionado = st.selectbox("Selecione o usuário que deseja remover:", usuarios)

        if st.button("Remover Usuário"):
            del config['credentials']['usernames'][usuario_selecionado]
            salvar_config(config)
            st.success(f"Usuário '{usuario_selecionado}' removido com sucesso!")
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar remover o usuário: {e}")


# ======== Código principal ========
config = carregar_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

try:
    authenticator.login()
except LoginError as e:
    st.error(e)

if st.session_state['authentication_status']:
    user_role = config['credentials']['usernames'][st.session_state['username']].get('role', 'user')

    st.sidebar.write(f'**Bem-vindo(a), {st.session_state["name"]}!**')
    authenticator.logout('Sair', 'sidebar')

    menu_options = {
        "Home": render_home,
        "Resetar Senha": lambda: render_resetar_senha(authenticator),
        "Atualizar Dados do Usuário": lambda: render_atualizar_dados(authenticator)
    }

    if user_role == 'admin':
        menu_options["Criar Novo Usuário"] = lambda: render_criar_usuario(authenticator, config)
        menu_options["Remover Usuário"] = lambda: render_remover_usuario(config)

    st.sidebar.markdown("---")
    selected_page = st.sidebar.radio("Navegue pelo menu:", list(menu_options.keys()))

    ### Descomente abaixo para exibir a imagem ###
    #image = Image.open("imagens/image.png")
    #st.image(image, width=200)
    ### Descomente acima para exibir a imagem ###

    #st.title(selected_page)
    menu_options[selected_page]()

elif st.session_state['authentication_status'] is False:
    st.error('Nome de usuário/senha incorretos')
elif st.session_state['authentication_status'] is None:
    st.warning('Por favor, insira seu nome de usuário e senha')