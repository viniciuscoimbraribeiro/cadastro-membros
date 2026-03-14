import streamlit as st
import pandas as pd
from datetime import date
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from streamlit_gsheets import GSheetsConnection
import time
import pickle  # Reativado
from google.auth.transport.requests import Request  # Reativado
from google_auth_oauthlib.flow import InstalledAppFlow  # Reativado

conn = st.connection("gsheets", type=GSheetsConnection)

# Para salvar os novos dados na sua planilha "Cadastro Igreja"
def salvar_na_planilha(dados_nova_linha):
    url = "hhttps://docs.google.com/spreadsheets/d/1obsFkjwgyBgTEi2YzGTcWlR7fjIwLgveDvnBh6wGdvc/edit?gid=0#gid=0"
    # Lemos o que já existe
    df_atual = conn.read(spreadsheet=url)
    # Criamos um DataFrame com a nova linha (garantindo que as colunas batam)
    df_novo_registro = pd.DataFrame([dados_nova_linha], columns=df_atual.columns)
    # Juntamos tudo
    df_final = pd.concat([df_atual, df_novo_registro], ignore_index=True)
    # Enviamos de volta para o Google
    conn.update(spreadsheet=url, data=df_final)


# --- FUNÇÃO AUXILIAR: Cálculo de Idade ---
def calcular_idade(data_nasc):
    if not data_nasc:
        return 0
    today = date.today()
    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

# 1. Conexão com Google Sheets
#def conectar_planilha():
#    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#    creds = ServiceAccountCredentials.from_json_keyfile_name("app-igreja-489815-20b366a946b6.json", scope)
#   client = gspread.authorize(creds)
#    return client.open_by_key("1obsFkjwgyBgTEi2YzGTcWlR7fjIwLgveDvnBh6wGdvc").sheet1

# 2. Conexão com Google Drive
def conectar_drive_pessoal():
    SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

# Funções de Folder e Upload
def get_or_create_folder(service, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id: query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    else:
        metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id: metadata['parents'] = [parent_id]
        folder = service.files().create(body=metadata, fields='id', supportsAllDrives=True).execute()
        return folder['id']

def upload_document(service, member_name, file):
    root_id = "1mtwff3O05vvw1r_QcEovgW8CkhV0d1p7"
    member_id = get_or_create_folder(service, member_name, parent_id=root_id)
    os.makedirs("temp", exist_ok=True)
    temp_path = os.path.join("temp", file.name)
    with open(temp_path, "wb") as f:
        f.write(file.getbuffer())
    try:
        metadata = {'name': file.name, 'parents': [member_id]}
        media = MediaFileUpload(temp_path, resumable=True)
        uploaded = service.files().create(body=metadata, media_body=media, fields='id, webViewLink').execute()
        del media 
        if os.path.exists(temp_path): os.remove(temp_path)
        return uploaded.get('webViewLink')
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass 
        raise e

# Configuração da página
st.set_page_config(page_title="Cadastro de Membros", page_icon="⛪")

# Exibir o logo centralizado
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Nota: O arquivo "logo_igreja.jpeg" deve estar na mesma pasta no GitHub
    try:
        st.image("logo_igreja.jpeg", width=200)
    except:
        st.warning("Arquivo de logo não encontrado.")

st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)

# CSS para remover sugestões de preenchimento e ajustar alinhamento da idade
st.markdown("""
    <style>
    input { autocomplete: off; }
    .age-box { display: flex; align-items: center; height: 100%; padding-top: 28px; }
    </style>
""", unsafe_allow_html=True)

if 'form_id' not in st.session_state:
    st.session_state['form_id'] = 0

aba = st.sidebar.radio("Navegação", ["Novo Cadastro", "🔍 Consulta", "📊 Estatísticas"])

# --- ABA: NOVO CADASTRO ---
if aba == "Novo Cadastro":
    if 'sucesso' in st.session_state:
        st.success("✅ Cadastro realizado com sucesso!")
        st.components.v1.html("<script>window.parent.document.querySelector('.main').scrollTo(0,0);</script>", height=0)
        del st.session_state['sucesso']

    st.header("📝 Formulário de Registro")
    fid = st.session_state['form_id']
    
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome Completo", key=f"nome_{fid}")
        st.write("Data de Nascimento")
        nascimento = st.date_input("Data de Nascimento", value=None, format="DD/MM/YYYY", min_value=date(1920, 1, 1), label_visibility="collapsed", key=f"nasc_{fid}")     
        endereco = st.text_input("Endereço", key=f"end_{fid}")
        profissao = st.text_input("Profissão", key=f"prof_{fid}")
        
        st.write("RG (Apenas números)")
        rg_txt = st.text_input("RG", label_visibility="collapsed", key=f"rg_{fid}")
        if rg_txt and not rg_txt.isdigit():
            st.warning("⚠️ RG deve conter apenas números.")
         
        st.write("CPF (Apenas números)")
        cpf_txt = st.text_input("CPF", label_visibility="collapsed", key=f"cpf_{fid}")
        if cpf_txt and not cpf_txt.isdigit():
            st.warning("⚠️ CPF deve conter apenas números.")

    with col2:
        nome_conjuge = st.text_input("Nome do Cônjuge", value="Não Aplicável", key=f"conj_{fid}")
        nome_pai = st.text_input("Nome do Pai", value="Não Aplicável", key=f"pai_{fid}")
        nome_mae = st.text_input("Nome da Mãe", key=f"mae_{fid}")
        estado_civil = st.selectbox("Estado Civil", ["", "Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)"], key=f"ec_{fid}")
        pastor = st.text_input("Pastor Responsável", key=f"past_{fid}")

    st.divider()
    st.subheader("👨‍👩‍👧‍👦 Informações dos Filhos")
    tem_filhos = st.checkbox("Tem filhos?", key=f"has_kids_{fid}")
    filhos_dados = [["Não Aplicável", "", 0] for _ in range(3)]
    
    if tem_filhos:
        for i in range(3):
            suffix = f"Filho(a) {i+1}"
            if i == 0 or st.checkbox(f"Adicionar {suffix}?", key=f"chk_f{i+1}_{fid}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                f_nome = c1.text_input(f"Nome {suffix}", key=f"f{i+1}n_{fid}")
                f_nasc = c2.date_input(f"Nascimento {suffix}", value=None, min_value=date(1900, 1, 1), key=f"f{i+1}d_{fid}")
                
                f_idade = calcular_idade(f_nasc) if f_nasc else 0
                c3.markdown(f'<div class="age-box">', unsafe_allow_html=True)
                c3.info(f"Idade: {f_idade}")
                c3.markdown('</div>', unsafe_allow_html=True)
                
                if f_nome:
                    filhos_dados[i] = [f_nome, f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade]

    st.divider()
    observacoes = st.text_area("Observações", key=f"obs_{fid}")
    documento_file = st.file_uploader("Documentos (PDF, JPG, PNG)", type=["pdf", "jpg", "png", "jpeg"], key=f"file_{fid}")
    
if st.button("Salvar Cadastro"):
    if not nome or not nascimento or not nome_mae or not estado_civil:
        st.error("⚠️ Preencha os campos obrigatórios.")
    else:
        try:
            # 1. Preparar os dados
            nova_linha = [
                nome, nascimento.strftime("%d/%m/%Y"), endereco, profissao,
                rg_txt or "Não Aplicável", cpf_txt or "Não Aplicável",
                nome_conjuge, nome_pai, nome_mae, estado_civil,
                filhos_dados[0][0], filhos_dados[0][1], filhos_dados[0][2],
                filhos_dados[1][0], filhos_dados[1][1], filhos_dados[1][2],
                filhos_dados[2][0], filhos_dados[2][1], filhos_dados[2][2],
                pastor, observacoes or "Não Aplicável", "Link do Drive aqui"
            ]

            # 2. Chama a função de salvamento
            salvar_na_planilha(nova_linha)

            st.session_state['sucesso'] = True
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")


# --- ABA: CONSULTA ---
elif aba == "🔍 Consulta":
    st.header("🔍 Consultar Membros")
    nome_busca = st.text_input("Digite o nome para pesquisar")
    
    if nome_busca:
        try:
            # ESTA É A PARTE NOVA:
            df = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1obsFkjwgyBgTEi2YzGTcWlR7fjIwLgveDvnBh6wGdvc/edit?gid=0#gid=0")
            dados = [df.columns.tolist()] + df.values.tolist() 
            
            if len(dados) > 1:
                registros = [[i + 2] + r for i, r in enumerate(dados[1:]) if nome_busca.lower() in str(r[0]).lower()]
                
                if registros:
                    for reg in registros:
                        idx_linha, linha = reg[0], reg[1:]
                        with st.expander(f"👤 {linha[0]}"):
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.markdown("### 📋 Dados Pessoais")
                                st.write(f"**Nascimento:** {linha[1]}")
                                st.write(f"**RG:** {linha[4]}")
                                st.write(f"**CPF:** {linha[5]}")
                                st.write(f"**Endereço:** {linha[2]}")
                                st.write(f"**Profissão:** {linha[3]}")
                            with c2:
                                st.markdown("### 👨‍👩‍👧 Família")
                                st.write(f"**Estado Civil:** {linha[9]}")
                                st.write(f"**Cônjuge:** {linha[6]}")
                                st.write(f"**Pai:** {linha[7]}")
                                st.write(f"**Mãe:** {linha[8]}")
                                st.write(f"**Filho 1:** {linha[10]} ({linha[12]} anos)")
                            with c3:
                                st.markdown("### ⛪ Igreja")
                                st.write(f"**Pastor:** {linha[19]}")

                            st.info(f"**Observações:** {linha[20]}")
                            if len(linha) > 21 and linha[21] != "Não Aplicável": 
                                st.link_button("📂 Abrir Documento no Drive", linha[21])
                            
                            st.divider()
                            col_pri, col_ed, col_ex = st.columns(3)
                            
                            if col_pri.button("🖨️ Imprimir", key=f"print_{idx_linha}"):
                                timestamp = time.time()
                                html_script = f"""
                                <script>
                                    var content = "<h2>Ficha de Membro</h2><p><b>Nome:</b> {linha[0]}</p>";
                                    var iFrame = document.createElement('iframe');
                                    iFrame.style.position = 'absolute'; iFrame.style.top = '-1000px';
                                    document.body.appendChild(iFrame);
                                    var doc = iFrame.contentDocument;
                                    doc.open(); doc.write(content); doc.close();
                                    setTimeout(function() {{ iFrame.contentWindow.print(); }}, 500);
                                </script>
                                """
                                st.components.v1.html(html_script, height=0)

                            if col_ed.button("📝 Editar", key=f"ed_{idx_linha}"):
                                st.session_state['editando_idx'] = idx_linha
                                st.session_state['dados_edit'] = linha
                            if col_ex.button("🗑️ Excluir", key=f"del_{idx_linha}"):
                                #sheet.delete_rows(idx_linha)
                                st.warning("A função de excluir será atualizada em breve.")
                                st.success("Excluído!")
                                st.rerun()
                else:
                    st.warning("Nenhum membro encontrado.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

# --- ABA: ESTATÍSTICAS (Placeholder para manter a navegação funcionando) ---
elif aba == "📊 Estatísticas":
    st.header("📊 Estatísticas")
    st.info("Funcionalidade em desenvolvimento.")
