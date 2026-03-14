import streamlit as st
import pandas as pd
from datetime import date
import os
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Cadastro de Membros", page_icon="⛪")

# Conexão da planilha via Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE APOIO ---

def salvar_na_planilha(dados_nova_linha):
    df_atual = conn.read() 
    df_novo_registro = pd.DataFrame([dados_nova_linha], columns=df_atual.columns)
    df_final = pd.concat([df_atual, df_novo_registro], ignore_index=True)
    conn.update(data=df_final)

def calcular_idade(data_nasc):
    if not data_nasc:
        return 0
    today = date.today()
    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

def conectar_drive_pessoal():
    creds_info = st.secrets["connections"]["gsheets"]
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed = false"
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
        
        # O robô faz o upload
        uploaded = service.files().create(
            body=metadata, 
            media_body=media, 
            fields='id, webViewLink',
            supportsAllDrives=True 
        ).execute()
        
        file_id = uploaded.get('id')

        # --- AÇÃO PARA EVITAR O ERRO 403 ---
        # O robô dá permissão de escrita para o seu e-mail pessoal. 
        # Isso vincula o arquivo à sua cota de 200GB.
        # Substitua o e-mail abaixo pelo seu e-mail principal (o da foto do Drive)
        email_dono = "seu_email_aqui@gmail.com" 
        
        try:
            service.permissions().create(
                fileId=file_id,
                body={'type': 'user', 'role': 'writer', 'emailAddress': email_dono},
                supportsAllDrives=True
            ).execute()
        except:
            pass # Se não conseguir dar permissão, ele segue assim mesmo

        if os.path.exists(temp_path): 
            os.remove(temp_path)
            
        return uploaded.get('webViewLink')
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

# --- INTERFACE ---

# Exibir o logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("logo_igreja.jpeg", width=200)
    except:
        st.warning("Logo não encontrado.")

st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)

if 'form_id' not in st.session_state:
    st.session_state['form_id'] = 0

aba = st.sidebar.radio("Navegação", ["Novo Cadastro", "🔍 Consulta", "📊 Estatísticas"])

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
        nascimento = st.date_input("Data de Nascimento", value=None, format="DD/MM/YYYY", min_value=date(1920, 1, 1), key=f"nasc_{fid}")     
        endereco = st.text_input("Endereço", key=f"end_{fid}")
        profissao = st.text_input("Profissão", key=f"prof_{fid}")
        rg_txt = st.text_input("RG (Apenas números)", key=f"rg_{fid}")
        cpf_txt = st.text_input("CPF (Apenas números)", key=f"cpf_{fid}")

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
            if i == 0 or st.checkbox(f"Adicionar Filho(a) {i+1}?", key=f"chk_f{i+1}_{fid}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                f_nome = c1.text_input(f"Nome Filho(a) {i+1}", key=f"f{i+1}n_{fid}")
                f_nasc = c2.date_input(f"Nasc. Filho(a) {i+1}", value=None, key=f"f{i+1}d_{fid}")
                f_idade = calcular_idade(f_nasc) if f_nasc else 0
                c3.info(f"Idade: {f_idade}")
                if f_nome:
                    filhos_dados[i] = [f_nome, f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade]

    st.divider()
    observacoes = st.text_area("Observações", key=f"obs_{fid}")
    documento_file = st.file_uploader("Anexar Documento", type=["pdf", "jpg", "png", "jpeg"], key=f"file_{fid}")
    
    if st.button("Salvar Cadastro"):
        if not nome or not nascimento or not nome_mae or not estado_civil:
            st.error("⚠️ Preencha os campos obrigatórios.")
        else:
            try:
                link_drive = "Não Anexado"
                if documento_file:
                    with st.spinner("Enviando para o Drive..."):
                        drive_service = conectar_drive_pessoal()
                        link_drive = upload_document(drive_service, nome, documento_file)

                nova_linha = [
                    nome, nascimento.strftime("%d/%m/%Y"), endereco, profissao,
                    rg_txt or "Não Aplicável", cpf_txt or "Não Aplicável",
                    nome_conjuge, nome_pai, nome_mae, estado_civil,
                    filhos_dados[0][0], filhos_dados[0][1], filhos_dados[0][2],
                    filhos_dados[1][0], filhos_dados[1][1], filhos_dados[1][2],
                    filhos_dados[2][0], filhos_dados[2][1], filhos_dados[2][2],
                    pastor, observacoes or "Não Aplicável", link_drive
                ]

                salvar_na_planilha(nova_linha)
                st.session_state['sucesso'] = True
                st.session_state['form_id'] += 1
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

elif aba == "🔍 Consulta":
    st.header("🔍 Pesquisar Membro")
    nome_busca = st.text_input("Nome do membro")
    if nome_busca:
        try:
            df = conn.read()
            # Filtro simples
            resultado = df[df.iloc[:, 0].str.contains(nome_busca, case=False, na=False)]
            if not resultado.empty:
                for idx, row in resultado.iterrows():
                    with st.expander(f"👤 {row.iloc[0]}"):
                        st.write(f"**Nascimento:** {row.iloc[1]}")
                        st.write(f"**CPF:** {row.iloc[5]}")
                        if row.iloc[21] != "Não Anexado":
                            st.link_button("📂 Ver Documento", row.iloc[21])
            else:
                st.warning("Nenhum registro encontrado.")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")

elif aba == "📊 Estatísticas":
    st.header("📊 Estatísticas")
    st.info("Funcionalidade em desenvolvimento.")
