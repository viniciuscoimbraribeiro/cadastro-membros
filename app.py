import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Cadastro de Membros", page_icon="⛪", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS (Via Secrets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO AUXILIAR: Cálculo de Idade ---
def calcular_idade(data_nasc):
    if not data_nasc:
        return 0
    today = date.today()
    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

# --- INTERFACE: LOGO E TÍTULO ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo_igreja.jpeg", width=200)

st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)

# Navegação lateral
aba = st.sidebar.radio("Navegação", ["Novo Cadastro", "🔍 Consulta"])

# --- ABA: NOVO CADASTRO ---
if aba == "Novo Cadastro":
    st.header("📝 Formulário de Registro")
    
    with st.form("cadastro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome Completo")
            nascimento = st.date_input("Data de Nascimento", value=None, format="DD/MM/YYYY", min_value=date(1920, 1, 1))
            endereco = st.text_input("Endereço")
            profissao = st.text_input("Profissão")
            rg = st.text_input("RG (Apenas números)")
            cpf = st.text_input("CPF (Apenas números)")

        with col2:
            nome_conjuge = st.text_input("Nome do Cônjuge", value="Não Aplicável")
            nome_pai = st.text_input("Nome do Pai", value="Não Aplicável")
            nome_mae = st.text_input("Nome da Mãe")
            estado_civil = st.selectbox("Estado Civil", ["", "Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)"])
            pastor = st.text_input("Pastor Responsável")

        observacoes = st.text_area("Observações")
        
        submitted = st.form_submit_button("Salvar Cadastro")
        
        if submitted:
            if not nome or not nascimento:
                st.error("⚠️ Nome e Data de Nascimento são obrigatórios.")
            else:
                # Criar DataFrame com o novo registro
                novo_membro = pd.DataFrame([{
                    "Nome Completo": nome,
                    "Data Nascimento": nascimento.strftime("%d/%m/%Y"),
                    "Endereço": endereco,
                    "Profissão": profissao,
                    "RG": rg,
                    "CPF": cpf,
                    "Cônjuge": nome_conjuge,
                    "Pai": nome_pai,
                    "Mãe": nome_mae,
                    "Estado Civil": estado_civil,
                    "Pastor": pastor,
                    "Observações": observacoes
                }])
                
                # Ler dados atuais e adicionar o novo
                dados_existentes = conn.read()
                dados_atualizados = pd.concat([dados_existentes, novo_membro], ignore_index=True)
                
                # Salvar no Google Sheets
                conn.update(data=dados_atualizados)
                st.success("✅ Cadastro realizado com sucesso!")

# --- ABA: CONSULTA ---
elif aba == "🔍 Consulta":
    st.header("🔍 Consultar Membros")
    nome_busca = st.text_input("Digite o nome para pesquisar")
    
    if nome_busca:
        df = conn.read()
        # Filtra os dados
        resultado = df[df['Nome Completo'].str.contains(nome_busca, case=False, na=False)]
        
        if not resultado.empty:
            for i, linha in resultado.iterrows():
                with st.expander(f"👤 {linha['Nome Completo']}"):
                    st.write(f"**CPF:** {linha['CPF']} | **Nascimento:** {linha['Data Nascimento']}")
                    st.write(f"**Endereço:** {linha['Endereço']}")
                    st.write(f"**Pastor Responsável:** {linha['Pastor']}")
                    st.info(f"**Obs:** {linha['Observações']}")
        else:
            st.warning("Nenhum membro encontrado.")
