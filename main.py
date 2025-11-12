import streamlit as st
import firebase_admin
from firebase_admin import credentials, db, storage
from datetime import datetime
import base64
import json
import uuid
import os

# =======================================================
# 🔑 1. CONFIGURAÇÃO DE SEGURANÇA E FIREBASE
# =======================================================
# NOTA: Para usar o firebase-admin, você precisa de um arquivo de credenciais JSON.
# Isso é mais seguro do que expor chaves no código.
# Para testes, vamos simular o uso de credenciais de ambiente ou st.secrets.

# Verifica se o Firebase já foi inicializado
if not firebase_admin._apps:
    try:
        # Para testes locais, sem credenciais reais, vamos inicializar com um mock
        # Isso NÃO funcionará para operações reais no Firebase.
        # Para produção, use st.secrets ou variáveis de ambiente.
        # Exemplo de como seria no secrets.toml:
        # [secrets]
        # firebase_credentials = '''
        # {
        #   "type": "service_account",
        #   "project_id": "comunica-guarulhos",
        #   "private_key_id": "...",
        #   "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        #   ...
        # }
        # '''
        # firebase_creds = json.loads(st.secrets["firebase_credentials"])
        # cred = credentials.Certificate(firebase_creds)
        # firebase_admin.initialize_app(cred, {
        #     'databaseURL': st.secrets["firebase_database_url"],
        #     'storageBucket': st.secrets["firebase_storage_bucket"]
        # })

        # Tentar carregar credenciais do st.secrets (recomendado para Streamlit Cloud)
        if "firebase_credentials" in st.secrets:
            firebase_creds = json.loads(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["firebase_database_url"],
                'storageBucket': st.secrets["firebase_storage_bucket"]
            })
            st.success("✅ Firebase inicializado com sucesso!")
        else:
            # Se não houver credenciais, inicializa sem conexão real
            st.warning("⚠️ Firebase não inicializado. Configure credenciais para usar funcionalidades do banco.")
            firebase_app = None

    except Exception as e:
        st.error(f"Erro ao inicializar o Firebase: {e}")
        firebase_app = None

# Funções para interagir com o banco e storage (quando configurado)
def get_firebase_db():
    if firebase_admin._apps:
        return db
    return None

def get_firebase_storage():
    if firebase_admin._apps:
        return storage
    return None

# =======================================================
# ⚙️ 2. ESTILOS (Incluindo os Ícones-Botão)
# =======================================================
# Baseado na sua intenção, usaremos o 'session_state' para gerenciar as telas
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def set_page(page_name):
    st.session_state.page = page_name
    st.rerun()

# HTML & CSS para Mobile-First e Botões de Ícones
st.set_page_config(page_title="Comunica Guarulhos", page_icon="📢", layout="centered")

st.markdown(f"""
<style>
    /* Estilos Básicos do Streamlit e Fundo */
    .stApp {{ background-color: #f8f9fa; }}
    /* Adiciona espaço para a barra de navegação fixa */
    .main {{ padding-bottom: 80px; }}
    h1, h2, h3 {{ color: #0d1b2a; text-align: center; }}

    /* -------------------------------------- */
    /* BARRA DE NAVEGAÇÃO INFERIOR FIXA */
    /* -------------------------------------- */
    .footer-nav {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        height: 70px;
        background-color: white;
        box-shadow: 0 -4px 6px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-around;
        align-items: center;
        z-index: 1000;
        padding: 0 5px;
    }}
    /* Estilo padrão do botão de navegação */
    .nav-button {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 5px;
        color: #6c757d;
        font-size: 0.75rem;
        font-weight: 500;
        text-decoration: none;
        transition: color 0.2s, background-color 0.2s;
        border: none;
        background: none;
        cursor: pointer;
        outline: none;
    }}
    /* Efeito hover e estado ativo */
    .nav-button:hover, .nav-button.active {{
        color: #f99417; /* Cor de destaque */
    }}
    .nav-button img {{
        width: 24px;
        height: 24px;
        margin-bottom: 3px;
    }}

    /* Botão Flutuante Central (Nova Comunicação) */
    .fab-container {{
        position: fixed;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1001;
    }}
    .fab-button {{
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #2a9d8f; /* Uma cor de ação */
        color: white;
        border: 4px solid white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        transition: background-color 0.2s;
        cursor: pointer;
    }}
    .fab-button:hover {{
        background-color: #218376;
    }}
    /* Cor de destaque para o botão ativo */
    .active-fab {{
        background-color: #f99417 !important;
    }}

    /* Estilo para as cards de problemas */
    .problem-card {{
        background: white;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid #f99417;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .footer {{
        font-size: 0.85rem;
        color: #64748b;
        text-align: center;
        margin-top: 2rem;
        padding: 1rem;
        border-top: 1px solid #e2e8f0;
    }}
    /* Esconde o menu Streamlit nativo para uma aparência mais limpa */
    #MainMenu, footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# Define os URLs externos para os botões de "Mais"
OUVIDORIA_URL = "https://www.guarulhos.sp.gov.br/ouvidoria-geral-do-municipio"
CAMARA_URL = "https://www.camaraguarulhos.sp.gov.br/"
SERVICOS_URL = "https://portal.guarulhos.sp.gov.br/servicos"

# =======================================================
# 🖼️ 3. Funções de Layout / Páginas
# =======================================================

def main_header():
    # Caminho relativo para os ícones dentro da pasta 'images'
    # O Streamlit Cloud e o Render servem arquivos estáticos dessa forma
    # Se o arquivo não for encontrado, o onerror esconde a imagem
    st.markdown(f"""
        <h1 style="text-align: left; margin-top: 0;">
            <img src='images/icone_logo.png' style='height: 30px; vertical-align: middle; margin-right: 10px;' onerror="this.style.display='none'">
            Comunica Guarulhos
        </h1>
    """, unsafe_allow_html=True)
    st.subheader("Sua voz constrói a cidade.")
    st.write("---")


def render_home_page():
    main_header()

    # ----------------------------------------------------
    # Atalhos para Serviços
    # ----------------------------------------------------
    st.subheader("Acesso Rápido")
    col1, col2 = st.columns(2)

    with col1:
        # Usa o ícone icone_ouvidoria.png
        st.markdown(f"""
            <a href="{OUVIDORIA_URL}" target="_blank" class="nav-button" style="width: 100%; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                <img src='images/icone_ouvidoria.png' alt="Ouvidoria" onerror="this.style.display='none'">
                <span>Ouvidoria</span>
            </a>
        """, unsafe_allow_html=True)
    with col2:
        # Usa o ícone icone_camara.png
        st.markdown(f"""
            <a href="{CAMARA_URL}" target="_blank" class="nav-button" style="width: 100%; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                <img src='images/icone_camara.png' alt="Câmara" onerror="this.style.display='none'">
                <span>Câmara Mun.</span>
            </a>
        """, unsafe_allow_html=True)

    # Usa o ícone icone_servicos.png
    st.markdown(f"""
        <a href="{SERVICOS_URL}" target="_blank" class="nav-button" style="width: 99%; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 20px;">
            <img src='images/icone_servicos.png' alt="Serviços Online" onerror="this.style.display='none'">
            <span>Serviços Online da Prefeitura</span>
        </a>
    """, unsafe_allow_html=True)

    # Exemplo de Estatísticas
    st.info("✅ *345* demandas resolvidas em 2025.")
    st.warning("🔥 *12* problemas de Iluminação em aberto.")


def render_denuncia_page():
    # --- VERIFICAÇÃO DE CONEXÃO ---
    firebase_connected = bool(firebase_admin._apps)
    if not firebase_connected:
        st.error("❌ Conexão com o banco de dados indisponível. Funcionalidade desativada temporariamente.")
        st.info("As denúncias não serão salvas até que o Firebase seja configurado.")
        # Mesmo assim, vamos permitir o preenchimento do formulário para demonstração
        st.warning("⚠️ Este é um modo de demonstração. Os dados NÃO serão salvos.")

    st.title("📢 Nova Comunicação")
    st.markdown("Relate o problema para a Ouvidoria Municipal de Guarulhos.")
    st.caption("Anonimato garantido.")

    # CATEGORIZAÇÃO
    tipo = st.selectbox("1. Tipo de Problema", [
        "Buraco na Via / Asfalto",
        "Lixo e Entulho Acumulado",
        "Iluminação Pública (Apagada/Queimada)",
        "Drenagem / Esgoto / Bueros",
        "Sinalização de Trânsito",
        "Árvore Caída / Poda",
        "Carro Abandonado",
        "Barulho / Poluição Sonora",
        "Outro / Geral"
    ], help="Selecione a categoria para direcionar o órgão correto.")

    # LOCALIZAÇÃO
    st.subheader("2. Localização")
    st.info("💡 *DICA:* Se estiver no celular, o app tentará preencher a latitude/longitude.")
    lat = st.text_input("Latitude", placeholder="Ex: -23.456", help="Atenção: A precisão é crucial.")
    lng = st.text_input("Longitude", placeholder="Ex: -46.543")

    # DESCRIÇÃO E FOTO
    st.subheader("3. Detalhes (Opcional)")
    descricao = st.text_area("Descrição do Problema", max_chars=300, placeholder="Ex: Buraco grande na esquina da Rua X com a Avenida Y, em frente à escola.")
    foto_upload = st.file_uploader("Foto (Opcional)", type=["jpg", "jpeg", "png"])

    if st.button("Enviar Comunicação", type="primary"):
        if not lat or not lng:
            st.error("❌ Por favor, informe a Latitude e a Longitude.")
            return

        # Validação de imagem
        foto_url = ""
        if foto_upload is not None:
            if foto_upload.size > 5 * 1024 * 1024: # 5MB
                st.error("❌ A imagem deve ter no máximo 5MB.")
                return
            file_ext = foto_upload.name.split('.')[-1].lower()
            if file_ext not in ['jpg', 'jpeg', 'png']:
                st.error("❌ Formato de imagem inválido. Use JPG ou PNG.")
                return

            # --- UPLOAD PARA STORAGE AINDA NÃO IMPLEMENTADO SEM CREDENCIAIS ---
            if firebase_connected:
                st.warning("⚠️ Upload de imagem não configurado. A denúncia será salva sem foto.")
            else:
                st.warning("⚠️ Modo demonstração: Upload de imagem não configurado.")

        # --- ENVIO PARA REALTIME DATABASE AINDA NÃO IMPLEMENTADO SEM CREDENCIAIS ---
        if firebase_connected:
            # db = get_firebase_db()
            # if db:
            #     try:
            #         denuncia = {
            #             "tipo": tipo,
            #             "descricao": descricao,
            #             "lat": lat,
            #             "lng": lng,
            #             "data": datetime.now().isoformat(),
            #             "status": "Enviada / Em Análise",
            #             "foto_url": foto_url,
            #             "confirmacoes": 1,
            #             "protocolo": f"GRL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            #         }
            #         result = db.reference("denuncias").push(denuncia)
            #         if 'user_denuncias_keys' not in st.session_state:
            #             st.session_state.user_denuncias_keys = []
            #         st.session_state.user_denuncias_keys.append(result.key)
            #         st.success(f"✅ Comunicação enviada com sucesso! Protocolo: *{denuncia['protocolo']}*")
            #         set_page('minhas_demandas')
            #     except Exception as e:
            #         st.error(f"❌ Erro ao enviar a comunicação: {str(e)}")
            # else:
            #     st.error("❌ Conexão com o banco de dados indisponível.")
            st.warning("⚠️ Modo demonstração: A denúncia NÃO foi salva no banco de dados.")
        else:
            st.warning("⚠️ Modo demonstração: A denúncia NÃO foi salva no banco de dados.")

        st.success(f"✅ Comunicação preenchida com sucesso! Protocolo: *DEMO-{uuid.uuid4().hex[:6].upper()}*")
        st.info("Acompanhe o status na aba *Minhas Demandas* (não persistente).")
        # Simula o salvamento apenas na sessão
        if 'user_denuncias_keys' not in st.session_state:
            st.session_state.user_denuncias_keys = []
        # Armazena um ID de demonstração
        demo_id = f"demo_{len(st.session_state.user_denuncias_keys) + 1}"
        st.session_state.user_denuncias_keys.append({
            "id": demo_id,
            "tipo": tipo,
            "descricao": descricao,
            "lat": lat,
            "lng": lng,
            "data": datetime.now().isoformat(),
            "status": "Demonstração",
            "foto_url": foto_url,
            "protocolo": f"DEMO-{uuid.uuid4().hex[:6].upper()}"
        })
        set_page('minhas_demandas')


def render_minhas_demandas_page():
    # Verifica se tem dados na sessão
    if 'user_denuncias_keys' not in st.session_state or not st.session_state.user_denuncias_keys:
        st.info("Você ainda não enviou nenhuma comunicação nesta sessão.")
        st.warning("⚠️ *Nota:* O histórico é mantido apenas enquanto você navega. Para um histórico permanente, seria necessário login e banco de dados.")
        return

    st.title("📋 Minhas Demandas")
    st.markdown("Acompanhe o status das comunicações que você enviou (apenas nesta sessão).")

    # Mostra os dados armazenados na sessão
    for d in st.session_state.user_denuncias_keys:
        status_color = "#f99417"
        if "Resolvida" in d['status']:
             status_color = "#2a9d8f"
        elif "Em Execução" in d['status']:
             status_color = "#1976d2"

        st.markdown(f"""
            <div class="problem-card" style="border-left: 5px solid {status_color};">
                <h4>{d['tipo']} - <span style="color: {status_color};">{d['status']}</span></h4>
                <p style="font-size: 0.9rem;">Protocolo: <strong>{d['protocolo']}</strong></p>
                <p>{d.get('descricao', 'Sem descrição.')[:70]}...</p>
                <p>Data: {d['data'][:10]}</p>
                {"<img src='" + d['foto_url'] + "' style='width: 100%; border-radius: 5px; margin-top: 10px;'>" if d.get('foto_url') else ""}
            </div>
        """, unsafe_allow_html=True)


def render_mapa_ocorrencias_page():
    st.title("🗺️ Ocorrências na Região")
    st.markdown("Veja e confirme problemas relatados por outros cidadãos.")

    st.info("❌ Ocorrências não configuradas sem banco de dados.")
    st.warning("⚠️ Modo demonstração: Esta funcionalidade não está disponível sem conexão com o banco de dados.")


# =======================================================
# 🚀 4. LÓGICA DE NAVEGAÇÃO E BARRA INFERIOR
# =======================================================

# Renderiza a página atual baseada no 'session_state'
if st.session_state.page == 'home':
    render_home_page()
elif st.session_state.page == 'minhas_demandas':
    render_minhas_demandas_page()
elif st.session_state.page == 'mapa_ocorrencias':
    render_mapa_ocorrencias_page()
elif st.session_state.page == 'nova_comunicacao':
    render_denuncia_page()


# ----------------------------------------------------
# Barra de Navegação Inferior (Fixa)
# ----------------------------------------------------

st.markdown("""
<div class="footer-nav">
""", unsafe_allow_html=True)

st.markdown(f"""
    <button class="nav-button {'active' if st.session_state.page == 'home' else ''}" onclick="window.parent.document.querySelector('[data-testid="stSidebarContent"]').scroll(0,0); set_page('home')">
        <img src='images/icone_home.png' alt="Início" onerror="this.style.display='none'">
        <span>Início</span>
    </button>
""", unsafe_allow_html=True)

st.markdown(f"""
    <button class="nav-button {'active' if st.session_state.page == 'minhas_demandas' else ''}" onclick="window.parent.document.querySelector('[data-testid="stSidebarContent"]').scroll(0,0); set_page('minhas_demandas')">
        <img src='images/icone_demandas.png' alt="Demandas" onerror="this.style.display='none'">
        <span>Demandas</span>
    </button>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="fab-container">
        <button class="fab-button {'active-fab' if st.session_state.page == 'nova_comunicacao' else ''}" onclick="window.parent.document.querySelector('[data-testid="stSidebarContent"]').scroll(0,0); set_page('nova_comunicacao')">
             +
        </button>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
    <button class="nav-button {'active' if st.session_state.page == 'mapa_ocorrencias' else ''}" onclick="window.parent.document.querySelector('[data-testid="stSidebarContent"]').scroll(0,0); set_page('mapa_ocorrencias')">
        <img src='images/icone_mapa.png' alt="Mapa" onerror="this.style.display='none'">
        <span>Mapa</span>
    </button>
""", unsafe_allow_html=True)

st.markdown(f"""
    <button class="nav-button" onclick="window.parent.document.querySelector('[data-testid="stSidebarContent"]').scroll(0,0); set_page('home')">
        <img src='images/icone_mais.png' alt="Mais" onerror="this.style.display='none'">
        <span>Mais</span>
    </button>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="footer">Comunica Guarulhos — Cidadania urbana com respeito.</div>', unsafe_allow_html=True)
