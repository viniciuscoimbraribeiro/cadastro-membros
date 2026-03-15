import streamlit as st
import pandas as pd
from datetime import date
import requests
import base64
import re
from streamlit_gsheets import GSheetsConnection



# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Cadastro de Membros", page_icon="⛪")

# Conexão da planilha via Secrets (Mantida para os dados)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE APOIO ---

def salvar_na_planilha(dados_nova_linha):
    df_atual = conn.read(ttl="10s") 
    df_novo_registro = pd.DataFrame([dados_nova_linha], columns=df_atual.columns)
    df_final = pd.concat([df_atual, df_novo_registro], ignore_index=True)
    conn.update(data=df_final)

def calcular_idade(data_nasc):
    if not data_nasc: return 0
    today = date.today()
    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

def upload_document_github(member_name, file):
    import datetime
    token = st.secrets["GITHUB_TOKEN"]
    # AJUSTE O NOME DO REPOSITÓRIO ABAIXO SE FOR DIFERENTE
    repo = "viniciuscoimbraribeiro/cadastro-membros"
    branch = "main"

    # Gerar um sufixo de tempo para garantir que o nome do arquivo seja ÚNICO
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{file.name.replace(' ', '_')}"
    
    # Criar um caminho de pasta limpo
    member_folder = member_name.replace(' ', '_').upper()
    path = f"cadastros/{member_folder}/{file_name}"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    
    content = base64.b64encode(file.getvalue()).decode()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": f"Doc: {member_name}", "content": content, "branch": branch}
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code in [200, 201]:
        # Retorna o link RAW (Direto) para visualização rápida
        return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    else:
        # Se ainda assim der erro de SHA, o erro aparecerá aqui com mais detalhes
        raise Exception(f"Erro GitHub: {response.json().get('message')}")

# --- INTERFACE ---



if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

aba = st.sidebar.radio("Navegação", ["Novo Cadastro", "🔍 Consulta", "📊 Estatísticas"])

if aba == "Novo Cadastro":
    # O logo e o título ficam aqui dentro para aparecerem SÓ nesta aba
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1]) 
    with col_l2:
        try:
            st.image("logo_igreja.jpeg", use_container_width=True)
        except:
            st.warning("Logo não encontrado.")

    st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)
    
    if 'sucesso' in st.session_state:
        st.success("✅ Cadastro realizado com sucesso!")
        del st.session_state['sucesso']

    fid = st.session_state['form_id']
    # ... segue o restante do formulário

    
    if 'sucesso' in st.session_state:
        st.success("✅ Cadastro realizado com sucesso!")
        del st.session_state['sucesso']

    #st.header("📝 Formulário de Registro")
    fid = st.session_state['form_id']
    
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome Completo", key=f"nome_{fid}")
        nascimento = st.date_input("Data de Nascimento (DD/MM/AAAA)", value=None, format="DD/MM/YYYY", min_value=date(1920, 1, 1), key=f"nasc_{fid}")     
        endereco = st.text_input("Endereço Completo", key=f"end_{fid}", autocomplete="address-line1")
        profissao = st.text_input("Profissão", key=f"prof_{fid}")

# --- RG com trava e bloqueio reforçado de Autofill ---
        rg_input = st.text_input(
            "Nº do Registro Geral", # Mudamos o nome para 'despistar' o navegador
            key=f"rg_raw_{fid}", 
            autocomplete="new-password", # Truque técnico: impede sugestões de cartões/senhas
        )
        rg_txt = re.sub(r'\D', '', rg_input)
        if rg_input != rg_txt:
            st.caption("⚠️ :orange[Use apenas Números.]")
        
        # --- CPF com trava e bloqueio reforçado de Autofill ---
        cpf_input = st.text_input(
            "Nº do Documento CPF", # Mudamos o nome para evitar gatilhos de pagamento
            key=f"cpf_raw_{fid}", 
            max_chars=11, 
            autocomplete="new-password", # Força o navegador a ignorar o histórico
        )
        cpf_txt = re.sub(r'\D', '', cpf_input)
        if cpf_input != cpf_txt:
            st.caption("⚠️ :orange[Use apenas os 11 números do CPF.]")

    with col2:
        nome_conjuge = st.text_input("Nome do Cônjuge", value="Não Aplicável", key=f"conj_{fid}")
        nome_pai = st.text_input("Nome do Pai", value="Não Aplicável", key=f"pai_{fid}")
        nome_mae = st.text_input("Nome da Mãe", key=f"mae_{fid}")
        estado_civil = st.selectbox("Estado Civil", ["Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)"], key=f"ec_{fid}")
        pastor = st.selectbox("Pastor Responsável", ["Adriano", "Albert", "Luis", "Não Aplicavel"], key=f"past_{fid}")
        #pastor = st.text_input("Pastor Responsável", key=f"past_{fid}")

    st.divider()
    st.subheader("👨‍👩‍👧‍👦 Filhos")
    tem_filhos = st.checkbox("Tem filhos?", key=f"has_kids_{fid}")
    filhos_dados = [["Não Aplicável", "", 0] for _ in range(3)]
    
    if tem_filhos:
        for i in range(3):
            if i == 0 or st.checkbox(f"Adicionar Filho(a) {i+1}?", key=f"chk_f{i+1}_{fid}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                f_nome = c1.text_input(f"Nome Filho {i+1}", key=f"f{i+1}n_{fid}")
                f_nasc = c2.date_input(f"Nasc. Filho {i+1} (DD/MM/AAAA)", value=None,format="DD/MM/YYYY", help="DD/MM/AAAA", key=f"f{i+1}d_{fid}")
                f_idade = calcular_idade(f_nasc) if f_nasc else 0
                c3.info(f"Idade: {f_idade}")
                if f_nome: filhos_dados[i] = [f_nome, f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade]

    st.divider()
    observacoes = st.text_area("Observações", key=f"obs_{fid}")
    documento_file = st.file_uploader("Anexar Documento", type=["pdf", "jpg", "png", "jpeg"], key=f"file_{fid}")
    
    if st.button("Salvar Cadastro"):
        if not nome or not nascimento or not nome_mae or not estado_civil:
            st.error("⚠️ Preencha os campos obrigatórios.")
        else:
            try:
                link_final = "Não Anexado"
                if documento_file:
                    with st.spinner("Enviando documento..."):
                        link_final = upload_document_github(nome, documento_file)

                nova_linha = [
                    nome, nascimento.strftime("%d/%m/%Y"), endereco, profissao,
                    rg_txt or "Não Aplicável", cpf_txt or "Não Aplicável",
                    nome_conjuge, nome_pai, nome_mae, estado_civil,
                    filhos_dados[0][0], filhos_dados[0][1], filhos_dados[0][2],
                    filhos_dados[1][0], filhos_dados[1][1], filhos_dados[1][2],
                    filhos_dados[2][0], filhos_dados[2][1], filhos_dados[2][2],
                    pastor, observacoes or "Não Aplicável", link_final
                ]

                salvar_na_planilha(nova_linha)
                st.session_state['sucesso'] = True
                st.session_state['form_id'] += 1
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

elif aba == "🔍 Consulta":
    st.header("🔍 Consultar e Gerenciar Membros")
    # Campo de texto e botão lado a lado ou um abaixo do outro
    nome_busca = st.text_input("Digite o nome para pesquisar", key="input_busca")
    botao_buscar = st.button("🔎 Buscar Membro", use_container_width=True)
    
    # A busca acontece se apertar ENTER (nome_busca) OU se clicar no BOTÃO (botao_buscar)
    if nome_busca or botao_buscar:
        try:
            # Forçamos a leitura sem cache para garantir dados frescos
            df = conn.read(ttl="10s")
            
            def normalizar(texto):
                import unicodedata
                return "".join(c for c in unicodedata.normalize('NFD', str(texto))
                             if unicodedata.category(c) != 'Mn').lower().strip()

            busca_limpa = normalizar(nome_busca)
            # Filtro inteligente
            indices_encontrados = df[df.iloc[:, 0].astype(str).apply(normalizar).str.contains(busca_limpa, na=False)].index

            if not indices_encontrados.empty:
                st.success(f"Encontrado(s) {len(indices_encontrados)} registro(s):")
                for idx in indices_encontrados:
                    linha = df.loc[idx].tolist()
                    
                    with st.expander(f"👤 {linha[0].upper()}"):
                        edit_key = f"edit_mode_{idx}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False

                        if not st.session_state[edit_key]:
                            # --- MODO VISUALIZAÇÃO ---
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.markdown("### 📋 Dados")
                            
                                # 1. Definimos a função de limpeza (mata o .0 e garante zeros à esquerda)
                            def formatar_documento(valor, tamanho):
                                if not valor or str(valor).lower() in ["nan", "none", ""]:
                                    return "Não Aplicável"
                                # Remove o .0 e pega apenas os números
                                limpo = re.sub(r'\D', '', str(valor).split('.')[0])
                                return limpo.zfill(tamanho)

                            # 2. Formatamos o CPF com a máscara
                            cpf_num = formatar_documento(linha[5], 11)
                            if cpf_num != "Não Aplicável":
                                cpf_formatado = f"{cpf_num[:3]}.{cpf_num[3:6]}.{cpf_num[6:9]}-{cpf_num[9:]}"
                            else:
                                cpf_formatado = cpf_num

                            # 3. Formatamos o RG (geralmente 9 dígitos, mas varia, então apenas limpamos o .0)
                            rg_formatado = formatar_documento(linha[4], 1) # 1 aqui apenas para não sumir com RGs curtos

                            # 4. Exibição na tela
                            st.write(f"**Nasc:** {linha[1]}")
                            st.write(f"**CPF:** {cpf_formatado}")
                            st.write(f"**RG:** {rg_formatado}")
                            st.write(f"**Profissão:** {linha[3]}")
                            
                            with c2:
                                st.markdown("### 👨‍👩‍👧 Família")
                                # Cônjuge com tratamento para vazio
                                conjuge = linha[6] if str(linha[6]).strip() and str(linha[6]) != "nan" else "Não Aplicável"
                                st.write(f"**Cônjuge:** {conjuge}")
                            
                                st.divider() # Pequena linha para separar cônjuge de filhos
                                st.write("**Lista de Filhos:**")

                                # Função rápida para tratar campos vazios ou 'nan' (comum em planilhas)
                                def tratar_campo(valor):
                                    if not valor or str(valor).lower() in ["nan", "none", ""]:
                                        return "Não Aplicável"
                                    return valor

                                # Exibição dos 3 Filhos (Colunas 10, 13 e 16 da sua planilha)
                                # Filho 1: Nome (linha[10]), Idade (linha[12])
                                f1_nome = tratar_campo(linha[10])
                                f1_idade = linha[12] if f1_nome != "Não Aplicável" else "-"
                                st.write(f"👶 **1º:** {f1_nome} ({f1_idade} anos)")

                                # Filho 2: Nome (linha[13]), Idade (linha[15])
                                f2_nome = tratar_campo(linha[13])
                                f2_idade = linha[15] if f2_nome != "Não Aplicável" else "-"
                                st.write(f"👶 **2º:** {f2_nome} ({f2_idade} anos)")

                                # Filho 3: Nome (linha[16]), Idade (linha[18])
                                f3_nome = tratar_campo(linha[16])
                                f3_idade = linha[18] if f3_nome != "Não Aplicável" else "-"
                                st.write(f"👶 **3º:** {f3_nome} ({f3_idade} anos)")
                            with c3:
                                st.markdown("### ⛪ Igreja")
                                st.write(f"**Pastor:** {linha[19]}")
                                st.info(f"**Obs:** {linha[20]}")

                            if len(linha) > 21 and "http" in str(linha[21]):
                                st.link_button("📂 Visualizar Documento", linha[21], use_container_width=True)

                            st.divider()
                            col_pri, col_ed, col_ex = st.columns(3)
                            
                            # 1. BOTÃO IMPRIMIR (Restaurado)
                            if col_pri.button("🖨️ Imprimir", key=f"btn_prt_{idx}"):
                                html_print = f"""
                                <script>
                                    var win = window.open('', '_blank');
                                    win.document.write('<html><body><h2>Ficha: {linha[0]}</h2><hr>');
                                    win.document.write('<p><b>CPF:</b> {linha[5]}</p><p><b>Endereço:</b> {linha[2]}</p>');
                                    win.document.write('</body></html>');
                                    win.document.close(); win.print();
                                </script>"""
                                st.components.v1.html(html_print, height=0)

                            # 2. BOTÃO EDITAR (Ativa o formulário)
                            if col_ed.button("📝 Editar Dados", key=f"btn_ed_{idx}"):
                                st.session_state[edit_key] = True
                                st.rerun()

                            # 3. BOTÃO EXCLUIR (Restaurado)
                            if col_ex.button("🗑️ Excluir", key=f"btn_del_{idx}"):
                                df_drop = df.drop(idx)
                                conn.update(data=df_drop)
                                st.success("Membro excluído com sucesso!")
                                st.rerun()

                        else:
                            # --- MODO EDIÇÃO ---
                            st.markdown(f"### 📝 Editando: {linha[0]}")
                            with st.form(key=f"form_edit_{idx}"):
                                col_e1, col_e2 = st.columns(2)
                                with col_e1:
                                    n_nome = st.text_input("Nome", value=linha[0])
                                    try:
                                        data_atual_dt = pd.to_datetime(linha[1], dayfirst=True).date()
                                    except:
                                        data_atual_dt = date.today() # Caso a data na planilha esteja inválid
                                    n_nasc = st.date_input("Nascimento", value=data_atual_dt, format="DD/MM/YYYY")
                                    n_end = st.text_input("Endereço", value=linha[2])
                                    n_cpf = st.text_input("CPF", value=linha[5])
                                with col_e2:
                                    n_conj = st.text_input("Cônjuge", value=linha[6])
                                    n_pastor = st.text_input("Pastor", value=linha[19])
                                    n_obs = st.text_area("Observações", value=linha[20])
                                
                                c_save, c_cancel = st.columns(2)
                                if c_save.form_submit_button("💾 Salvar"):
                                    df.at[idx, df.columns[0]] = n_nome
                                    df.at[idx, df.columns[1]] = n_nasc
                                    df.at[idx, df.columns[2]] = n_end
                                    df.at[idx, df.columns[5]] = n_cpf
                                    df.at[idx, df.columns[6]] = n_conj
                                    df.at[idx, df.columns[19]] = n_pastor
                                    df.at[idx, df.columns[20]] = n_obs
                                    conn.update(data=df)
                                    st.session_state[edit_key] = False
                                    st.rerun()
                                
                                if c_cancel.form_submit_button("❌ Cancelar"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
            else:
                st.warning("Nenhum membro encontrado.")
        except Exception as e:
            st.error(f"Erro: {e}")
                        

elif aba == "📊 Estatísticas":
    st.info("Funcionalidade em desenvolvimento.")
