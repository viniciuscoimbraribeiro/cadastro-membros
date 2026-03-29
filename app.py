import streamlit as st
import pandas as pd
import requests
import base64
import re
import datetime
from streamlit_gsheets import GSheetsConnection
import unicodedata
import streamlit.components.v1 as components
import time

# 1. Configuração da página
st.set_page_config(page_title="IBPS Sumaré", page_icon="logo_igreja.png", layout="wide")

# 2. Injeção Direta de Metadados (Substituindo o fix_icon anterior)
# O link ?raw=true que você achou é perfeito
icon_url = "https://github.com/viniciuscoimbraribeiro/cadastro-membros/blob/main/logo_igreja.png?raw=true"

st.markdown(f"""
    <head>
        <link rel="apple-touch-icon" href="{icon_url}">
        <link rel="icon" type="image/png" href="{icon_url}">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
""", unsafe_allow_html=True)


# 1. Função para converter imagem para base64
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None
# 2. Executa a conversão
img_64 = get_base64("logo_igreja.png")

# 3. Injeta uma única vez o HTML
if img_64:
    st.markdown(
        f"""
        <link rel="apple-touch-icon" href="data:image/png;base64,{img_64}">
        <link rel="icon" sizes="192x192" href="data:image/png;base64,{img_64}">
        """,
        unsafe_allow_html=True
    )




st.sidebar.image("logo_igreja.png", use_container_width=True)
st.sidebar.divider()


# Função 1: Para limpar CPF (Mata o .0 e formata com pontos/traço)
def limpar_e_formatar_cpf(valor):
    if not valor or str(valor).lower() in ["nan", "none", ""]:
        return "Não Aplicável"
    # Remove .0 e qualquer coisa que não seja número
    limpo = re.sub(r'\D', '', str(valor).split('.')[0])
    if not limpo: return "Não Aplicável"
    # Garante 11 dígitos e aplica máscara
    c = limpo.zfill(11)
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

# Função 2: Para limpar RG (Apenas mata o .0)
def limpar_rg(valor):
    if not valor or str(valor).lower() in ["nan", "none", ""]:
        return "Não Aplicável"
    return re.sub(r'\D', '', str(valor).split('.')[0])

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IBPS Sumaré", page_icon="⛪")

# Conexão da planilha via Secrets (Mantida para os dados)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE APOIO ---

def salvar_na_planilha(dados_nova_linha):
    df_atual = conn.read(ttl="10s") 
    df_novo_registro = pd.DataFrame([dados_nova_linha], columns=df_atual.columns)
    df_final = pd.concat([df_atual, df_novo_registro], ignore_index=True)
    conn.update(data=df_final)

#def calcular_idade(data_nasc):
#    if not data_nasc: return 0
#    today = date.today()
#    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

def calcular_idade(data_nasc):
    if not data_nasc: return 0
    # Usamos datetime.date.today() para evitar o erro de NameError
    today = datetime.date.today()
    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

def upload_document_github(member_name, file):
   # import datetime
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

#aba = st.sidebar.radio("Navegação", ["Novo Cadastro", "🔍 Consulta", "Catálogo de Serviços", "📊 Estatísticas"])



# --- NAVEGAÇÃO LATERAL ---
with st.sidebar:
    st.title("Navegação")
    aba = st.radio("Ir para:", ["📝 Novo Cadastro", "🔍 Consulta de Membros", "🛠️ Catálogo de Serviços", "📊 Estatísticas"])


if aba == "📝 Novo Cadastro":
    # O logo e o título ficam aqui dentro para aparecerem SÓ nesta aba
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1]) 


    st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)
    
    # --- MENSAGEM DE SUCESSO TEMPORÁRIA ---
    if 'sucesso' in st.session_state:
        placeholder = st.empty() # Cria um espaço vazio
        with placeholder.container():
            st.success("✅ Cadastro realizado com sucesso!")
        
        time.sleep(5) # Espera 5 segundos
        placeholder.empty() # Remove a mensagem da tela
        del st.session_state['sucesso'] # Limpa o estado para não repetir

    fid = st.session_state['form_id']
    
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome Completo", key=f"nome_{fid}")
        nascimento = st.date_input(
            "Data de Nascimento (DD/MM/AAAA)", value=None, format="DD/MM/YYYY", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today(), key=f"nasc_{fid}"
        )        
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
        estado_civil = st.selectbox("Estado Civil", ["Solteiro(a)", "Casado(a)", "União Estável", "Divorciado(a)", "Viúvo(a)"], key=f"ec_{fid}")
        nome_conjuge = "Não Aplicável"
        dt_nasc_conjuge = "Não Aplicável"
        prof_conjuge = "Não Aplicável"
        if estado_civil in ["Casado(a)", "União Estável"]:
           
            nome_conjuge = st.text_input("Nome do Cônjuge", key=f"nome_conj_{fid}")

            # 1. Calendário corrigido com limites de data (1900 até hoje)
            # O value=None faz o campo começar limpo, sem data padrão
            data_obj_conj = st.date_input(
                "Data Nascimento Cônjuge", 
                value=None,
                min_value=datetime.date(1900, 1, 1),
                max_value=datetime.date.today(),
                format="DD/MM/YYYY", 
                key=f"dt_calend_conj_{fid}"
            )
            
            if data_obj_conj:
                dt_nasc_conjuge = data_obj_conj.strftime("%d/%m/%Y")
            else:
                dt_nasc_conjuge = ""
            prof_conjuge = st.text_input("Profissão do Cônjuge", key=f"prof_conj_input_extra_{fid}")     
            
    
        # 3. Campos que SEMPRE aparecem (Pai e Mãe) - Fora do IF
        nome_mae = st.text_input("Nome da Mãe", key=f"mae_{fid}")
        nome_pai = st.text_input("Nome do Pai", key=f"pai_{fid}")




    
    st.divider()
    st.subheader("👨‍👩‍👧‍👦 Filhos")
    tem_filhos = st.checkbox("Tem filhos?", key=f"has_kids_{fid}")
    #filhos_dados = [["Não Aplicável", "", 0] for _ in range(3)]
    filhos_dados = [["Não Aplicável", "", 0, "Não Aplicável"] for _ in range(3)]
    
    if tem_filhos:
        for i in range(3):
            if i == 0 or st.checkbox(f"Adicionar Filho(a) {i+1}?", key=f"chk_f{i+1}_{fid}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                f_nome = c1.text_input(f"Nome Filho {i+1}", key=f"f{i+1}n_{fid}")
                f_nasc = c2.date_input(
                    f"Nasc. Filho {i+1} (DD/MM/AAAA)", 
                    value=None,
                    format="DD/MM/YYYY", 
                    min_value=datetime.date(1900, 1, 1), # Destrava para o passado
                    max_value=datetime.date.today(),      # Trava no dia de hoje
                    help="Selecione a data de nascimento", 
                    key=f"f{i+1}d_{fid}"
                )
                f_idade = calcular_idade(f_nasc) if f_nasc else 0
                c3.info(f"Idade: {f_idade}")
                #if f_nome: filhos_dados[i] = [f_nome, f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade]
                if f_nome: filhos_dados[i] = [f_nome, f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade, "Não Aplicável"]



# --- SEÇÃO IGREJA (Centralizada) ---
    st.divider()
    st.subheader("⛪ Igreja")
    
    # 1. Batismo do Membro Principal
    bat_membro = st.selectbox("Membro é Batizado?", ["Selecione...", "Sim", "Não"], key=f"bat_mem_principal_{fid}")
    
    # 2. Batismo do Cônjuge (Depende do Estado Civil selecionado lá em cima)
    if estado_civil in ["Casado(a)", "União Estável"]:
        bat_conjuge = st.selectbox(f"O Cônjuge ({nome_conjuge}) é Batizado?", ["Selecione...", "Sim", "Não"], key=f"bat_conj_igreja_{fid}")
    else:
        bat_conjuge = "Não Aplicável"

    # 3. Batismo dos Filhos (Depende se 'tem_filhos' e se idade >= 18)
    if tem_filhos:
        for i in range(3):
            # Só processamos se o nome do filho foi preenchido na seção anterior
            nome_f = filhos_dados[i][0]
            idade_f = filhos_dados[i][2]
            
            if nome_f != "Não Aplicável" and nome_f != "":
                if idade_f >= 18:
                    f_bat_input = st.selectbox(f"Filho(a) {i+1} ({nome_f}) é Batizado?", ["Selecione...", "Sim", "Não"], key=f"bat_f{i+1}_igreja_{fid}")
                    # Atualiza a lista de dados dos filhos com a resposta
                    filhos_dados[i][3] = f_bat_input
                else:
                    # Se for menor, já definimos como "Não Aplicável" ou "Não" automaticamente
                    filhos_dados[i][3] = "Não Aplicável"
                    st.caption(f"ℹ️ {nome_f} é menor de idade ({idade_f} anos). Batismo não registrado.")

    # 4. Pastor Responsável
    pastor = st.selectbox("Pastor Responsável", ["Selecione...", "Adriano", "Albert", "Luis", "Não Aplicável"], key=f"past_igreja_{fid}")
    
    
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

                # MONTAGEM DA LINHA - CONFERIR COM COLUNAS DO SHEETS
                nova_linha = [
                    nome,                             # Col A
                    nascimento.strftime("%d/%m/%Y"),  # Col B
                    bat_membro,                       # Col C (NOVA POSIÇÃO)
                    endereco,                         # Col D
                    profissao,                        # Col E
                    rg_txt or "Não Aplicável",        # Col F
                    cpf_txt or "Não Aplicável",       # Col G
                    nome_conjuge,                     # Col H
                    dt_nasc_conjuge,                  # Col I
                    prof_conjuge,                     # Col J
                    bat_conjuge,                      # Col K (NOVA COLUNA)
                    nome_pai,                         # Col L
                    nome_mae,                         # Col M
                    estado_civil,                     # Col N
                    filhos_dados[0][0],               # Col O (Nome F1)
                    filhos_dados[0][1],               # Col P (Nasc F1)
                    filhos_dados[0][2],               # Col Q (Idade F1)
                    filhos_dados[0][3],               # Col R (Batismo F1 - NOVA)
                    filhos_dados[1][0],               # Col S (Nome F2)
                    filhos_dados[1][1],               # Col T (Nasc F2)
                    filhos_dados[1][2],               # Col U (Idade F2)
                    filhos_dados[1][3],               # Col V (Batismo F2 - NOVA)
                    filhos_dados[2][0],               # Col W (Nome F3)
                    filhos_dados[2][1],               # Col X (Nasc F3)
                    filhos_dados[2][2],               # Col Y (Idade F3)
                    filhos_dados[2][3],               # Col Z (Batismo F3 - NOVA)
                    pastor,                           # Col AA
                    observacoes or "Não Aplicável",   # Col AB
                    link_final                        # Col AC
                ]

                salvar_na_planilha(nova_linha)
                st.session_state['sucesso'] = True
                st.session_state['form_id'] += 1
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
                pass 
elif aba == "🔍 Consulta de Membros":
    # --- NOVO: LOGICA DE RESET DE SEGURANÇA ---
    # Se a aba anterior era outra, resetamos a senha para garantir o bloqueio inicial
    if "ultima_aba" not in st.session_state:
        st.session_state.ultima_aba = aba
    
    if st.session_state.ultima_aba != aba:
        st.session_state.autenticado_consulta = False
        st.session_state.ultima_aba = aba

    # 1. Inicializar o estado de autenticação se não existir
    if "autenticado_consulta" not in st.session_state:
        st.session_state.autenticado_consulta = False

    # 2. VERIFICAÇÃO DO BLOQUEIO (GATE)
    if not st.session_state.autenticado_consulta:
        st.header("🔐 Acesso Restrito")
        # Interface limpa conforme image_a705c5.png
        senha_acesso = st.text_input("Digite a senha para acessar a consulta", type="password", key="senha_admin_definitiva")
        
        if senha_acesso == "1234":
            st.session_state.autenticado_consulta = True
            st.rerun()
        elif senha_acesso != "":
            st.error("❌ Senha incorreta.")
        else:
            st.info("Aguardando senha para liberar o painel...")
        
        # O st.stop() aqui impede que as abas de pesquisa/lista (image_a705c5.png) apareçam
        st.stop() 

    # --- 3. SE CHEGOU AQUI, ESTÁ AUTENTICADO ---
    # Botão de bloqueio manual (conforme solicitado)
    if st.button("🔒 Bloquear Acesso"):
        st.session_state.autenticado_consulta = False
        st.rerun()
        
    st.header("🔍 Consultar e Gerenciar Membros")

    # Re-importar para garantir que as funções funcionem neste escopo
    import unicodedata
    import re

    def normalizar(texto):
        return "".join(c for c in unicodedata.normalize('NFD', str(texto))
                       if unicodedata.category(c) != 'Mn').lower().strip()

    def tratar_campo(valor):
        if not valor or str(valor).lower() in ["nan", "none", "", "não aplicável"]: 
            return "Não Aplicável"
        return valor

    # --- O RESTANTE DO SEU SCRIPT DE RENDERIZAÇÃO E ABAS SEGUE AQUI ---
    # (Mantenha a função renderizar_membro_completo e as st.tabs abaixo deste bloco)

    # --- FUNÇÃO MESTRE: SEU CÓDIGO ORIGINAL INTEGRAL COM SUFIXO ---
    def renderizar_membro_completo(idx, df_contexto, sufixo):
        membro = df_contexto.loc[idx]
        nome_exibicao = str(membro['Nome Completo']).upper()

        # --- [PROCESAMENTO DE DADOS NO TOPO - EVITA UNBOUNDLOCALERROR] ---
        # CPF
        val_cpf = str(membro['CPF']).strip().replace('.0', '')
        cpf_limpo = re.sub(r'\D', '', val_cpf)
        if len(cpf_limpo) >= 1:
            c = cpf_limpo.zfill(11)
            cpf_f = f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
        else: 
            cpf_f = "Não Aplicável"
        
        # RG
        val_rg = str(membro['RG']).strip().replace('.0', '')
        rg_f = re.sub(r'\D', '', val_rg)
        if not rg_f: rg_f = "Não Aplicável"
        
        # Variáveis auxiliares
        conjuge = tratar_campo(membro['Nome Completo Conjuge'])
        # ----------------------------------------------------------------

        with st.expander(f"👤 {nome_exibicao}"):
            edit_key = f"edit_mode_{idx}_{sufixo}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            if not st.session_state[edit_key]:
                # --- MODO VISUALIZAÇÃO (RESTAURADO COM TODAS AS FUNÇÕES) ---
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("### 📋 Dados")
                    st.write(f"**Nasc:** {membro['Data Nascimento']}")
                    st.write(f"**CPF:** {cpf_f}")
                    st.write(f"**RG:** {rg_f}")
                    st.write(f"**Profissão:** {membro['Profissão']}")

                with c2:
                    st.markdown("### 👨‍👩‍👧 Família")
                    # Lógica do Cônjuge (Restaurada conforme original)
                    if conjuge != "Não Aplicável":
                        st.write(f"**Cônjuge:** {conjuge}")
                        dt_nasc_c = tratar_campo(membro['Data Nascimento Cônjuge'])
                        prof_c = tratar_campo(membro['Profissão Cônjuge'])
                        if dt_nasc_c != "Não Aplicável": st.write(f"🎂 **Nasc. Cônjuge:** {dt_nasc_c}")
                        if prof_c != "Não Aplicável": st.write(f"💼 **Prof. Cônjuge:** {prof_c}")
                    else:
                        st.write("**Cônjuge:** Não Aplicável")
                    
                    st.write(f"**Pai:** {tratar_campo(membro['Nome do Pai'])}")
                    st.write(f"**Mãe:** {tratar_campo(membro['Nome da Mãe'])}")
                    st.write(f"**Estado Civil:** {tratar_campo(membro['Estado Civil'])}")
                    
                    st.write("**Lista de Filhos:**")
                    tem_filho = False
                    for i in range(1, 4):
                        f_nome = tratar_campo(membro[f'Nome do Filho (a) - {i}'])
                        if f_nome != "Não Aplicável":
                            idade = membro[f'Idade do Filho(a) - {i}']
                            st.write(f"👶 **{i}º:** {f_nome} ({idade} anos)")
                            tem_filho = True
                    if not tem_filho: st.caption("Nenhum filho registrado.")

                with c3:
                    st.markdown("### ⛪ Igreja")
                    st.write(f"**Batizado:** {membro['Batizado Membro']}")
                    st.write(f"**Pastor:** {membro['Pastor Responsável']}")
                    st.info(f"**Obs:** {tratar_campo(membro['Observações'])}")
                    
                    # Link de Documentos (Restaurado)
                    doc_url = str(membro['Documentos'])
                    if "http" in doc_url:
                        st.link_button("📂 Visualizar Documento", doc_url, use_container_width=True)

                st.divider()
                col_pri, col_ed, col_ex = st.columns(3)
                
                # Botão Imprimir (Seu código completo de HTML)
                if col_pri.button("🖨️ Imprimir Ficha", key=f"btn_prt_{idx}_{sufixo}"):
                    filhos_html = ""
                    for i in range(1, 4):
                        f_n = tratar_campo(membro[f'Nome do Filho (a) - {i}'])
                        if f_n != "Não Aplicável":
                            f_id = membro[f'Idade do Filho(a) - {i}']
                            filhos_html += f"<li>{f_n} ({f_id} anos)</li>"
                    if not filhos_html: filhos_html = "<li>Nenhum filho registrado</li>"
                    
                    html_print = f"""
                    <script>
                        var win = window.open('', '_blank');
                        win.document.write('<html><head><title>Ficha de Membro - {membro['Nome Completo']}</title>');
                        win.document.write('<style>');
                        win.document.write('body {{ font-family: Arial, sans-serif; padding: 40px; color: #333; }}');
                        win.document.write('h2 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}');
                        win.document.write('.section {{ margin-top: 20px; border: 1px solid #eee; padding: 15px; border-left: 5px solid #2c3e50; background: #f9f9f9; }}');
                        win.document.write('.section-title {{ font-weight: bold; font-size: 1.1em; text-decoration: underline; margin-bottom: 10px; display: block; }}');
                        win.document.write('.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}');
                        win.document.write('</style></head><body>');
                        
                        win.document.write('<h2>FICHA CADASTRAL DE MEMBRO</h2>');
                        
                        // SEÇÃO 1: DADOS PESSOAIS
                        win.document.write('<div class="section"><span class="section-title">I. DADOS PESSOAIS</span>');
                        win.document.write('<div class="grid">');
                        win.document.write('<div><b>Nome:</b> {membro['Nome Completo']}</div>');
                        win.document.write('<div><b>Data de Nasc.:</b> {membro['Data Nascimento']}</div>');
                        win.document.write('<div><b>CPF:</b> {cpf_f}</div>');
                        win.document.write('<div><b>RG:</b> {rg_f}</div>');
                        win.document.write('<div><b>Profissão:</b> {membro['Profissão']}</div>');
                        win.document.write('<div><b>Estado Civil:</b> {membro['Estado Civil']}</div>');
                        win.document.write('</div></div>');
                        
                        // SEÇÃO 2: FAMÍLIA
                        win.document.write('<div class="section"><span class="section-title">II. FAMÍLIA E FILHOS</span>');
                        win.document.write('<b>Cônjuge:</b> {conjuge}<br>');
                        if ("{conjuge}" != "Não Aplicável") {{
                             win.document.write('<b>Profissão Cônjuge:</b> {tratar_campo(membro['Profissão Cônjuge'])}<br>');
                        }}
                        win.document.write('<b>Pai:</b> {tratar_campo(membro['Nome do Pai'])}<br>');
                        win.document.write('<b>Mãe:</b> {tratar_campo(membro['Nome da Mãe'])}<br>');
                        win.document.write('<b>Filhos:</b><ul>{filhos_html}</ul>');
                        win.document.write('</div>');
                        
                        // SEÇÃO 3: ECLESIÁSTICO
                        win.document.write('<div class="section"><span class="section-title">III. DADOS ECLESIÁSTICOS</span>');
                        win.document.write('<div class="grid">');
                        win.document.write('<div><b>Batizado:</b> {membro['Batizado Membro']}</div>');
                        win.document.write('<div><b>Pastor Responsável:</b> {membro['Pastor Responsável']}</div>');
                        win.document.write('</div>');
                        win.document.write('<p><b>Observações:</b> {tratar_campo(membro['Observações'])}</p>');
                        win.document.write('</div>');
                        
                        win.document.write('<p style="text-align:center; font-size: 0.8em; margin-top: 50px;">Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}</p>');
                        

                        win.document.write('</body></html>');
                        win.document.close();
                        setTimeout(function() {{ win.print(); }}, 800);
                    </script>"""
                    st.components.v1.html(html_print, height=0)
                    st.toast("Preparando ficha...")

                if col_ed.button("📝 Editar Dados", key=f"btn_ed_{idx}_{sufixo}"):
                    st.session_state[edit_key] = True
                    st.rerun()

                if col_ex.button("🗑️ Excluir", key=f"btn_del_{idx}_{sufixo}"):
                    df_drop = df_contexto.drop(idx)
                    conn.update(data=df_drop)
                    st.success("Excluído!")
                    st.rerun()

            else:
                # --- MODO EDIÇÃO (REVISADO E COMPLETO) ---
                st.markdown(f"### 📝 Editando: {membro['Nome Completo']}")
                with st.form(key=f"form_edit_{idx}_{sufixo}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        n_nome = st.text_input("Nome", value=membro['Nome Completo'])
                        n_cpf = st.text_input("CPF (Somente Números)", value=cpf_limpo)
                        n_rg = st.text_input("RG (Somente Números)", value=rg_f)
                    with col_e2:
                        n_batizado = st.selectbox("Batizado", ["Sim", "Não"], index=0 if membro['Batizado Membro'] == "Sim" else 1)
                        n_est_civil = st.text_input("Estado Civil", value=membro['Estado Civil'])
                        n_obs = st.text_area("Observações", value=membro['Observações'])

                    c_save, c_canc = st.columns(2)
                    if c_save.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                        df_contexto.at[idx, 'Nome Completo'] = n_nome
                        df_contexto.at[idx, 'CPF'] = n_cpf
                        df_contexto.at[idx, 'RG'] = n_rg
                        df_contexto.at[idx, 'Estado Civil'] = n_est_civil
                        df_contexto.at[idx, 'Batizado Membro'] = n_batizado
                        df_contexto.at[idx, 'Observações'] = n_obs
                        conn.update(data=df_contexto)
                        st.session_state[edit_key] = False
                        st.rerun()
                    
                    if c_canc.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state[edit_key] = False
                        st.rerun()

    # --- ABAS DE INTERFACE ---
    tab_busca, tab_lista = st.tabs(["🔎 Pesquisar por Nome", "📋 Lista Geral"])

    with tab_busca:
        nome_busca = st.text_input("Digite o nome para pesquisar", key="input_busca_original")
        if nome_busca:
            df = conn.read(ttl="5s")
            busca_limpa = normalizar(nome_busca)
            indices = df[df['Nome Completo'].astype(str).apply(normalizar).str.contains(busca_limpa, na=False)].index
            if not indices.empty:
                for idx in indices:
                    renderizar_membro_completo(idx, df, "busca")
            else:
                st.warning("Nenhum membro encontrado.")

    with tab_lista:
        df_full = conn.read(ttl="10s")
        df_full = df_full.sort_values(by=df_full.columns[0])            
        st.write(f"Total: {len(df_full)} membros")
        for idx in df_full.index:
            renderizar_membro_completo(idx, df_full, "lista")
            
# --- BLOCO DE BACKUP (Inserir ao final da tab_lista) ---
    st.divider()
    st.subheader("💾 Backup de Segurança")
        
    # Criamos o arquivo Excel em memória
    import io
    buffer = io.BytesIO()
        
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Exporta o DataFrame atual para o Excel
        df_full.to_excel(writer, index=False, sheet_name='Membros')
            
    st.download_button(
        label="📥 Baixar Lista de Membros (Excel)",
        data=buffer,
        file_name=f"backup_membros_{pd.Timestamp.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Clique aqui para baixar uma cópia de segurança de todos os dados da planilha."
    )
            
# --- ABA 3: CATÁLOGO DE SERVIÇOS (Aqui entra o Filtro de Profissionais) ---
elif aba == "🛠️ Catálogo de Serviços":
    st.header("🛠️ Catálogo de Serviços e Profissões")
    st.write("Pesquise por profissionais dentro da nossa comunidade.")
    
    prof_busca = st.text_input("O que você procura? (Ex: Pedreiro, Advogado, Calheiro, Encandor, etc...)")
    
    if st.button("🔎 Filtrar Profissionais", key="btn_filtro_catalogo", use_container_width=True):
        if prof_busca:
            df = conn.read(ttl="10s")
            # Filtra pela Profissão (Coluna 3)
            encontrados = df[df.iloc[:, 3].astype(str).str.contains(prof_busca, case=False, na=False)]
            
            if not encontrados.empty:
                st.info(f"Encontramos {len(encontrados)} profissional(is):")
                for _, row in encontrados.iterrows():
                    with st.container():
                        st.subheader(f"👤 {row.iloc[0]}")
                        st.write(f"🛠️ **Especialidade:** {row.iloc[3]}")
                        st.write("📞 **Contato:** Solicite à secretaria") 
                        st.divider()
            else:
                st.warning(f"Ainda não temos '{prof_busca}' cadastrado.")

elif aba == "📊 Estatísticas":
        st.header("📊 Painel Estatístico de Membros")
        st.write("Análise demográfica e espiritual consolidada da congregação.")

        # 1. Carregamento de Dados
        with st.spinner("Processando indicadores..."):
            df = conn.read(ttl="1s")

        if df.empty:
            st.warning("⚠️ Nenhum dado encontrado. Cadastre membros para visualizar os gráficos.")
        else:
 
            # --- MOTOR DE CÁLCULO MANUAL---
            def calcular_idade_manual(nascimento):
                try:
                    s = str(nascimento).strip()
                    if not s or s.lower() in ["nan", "none", "", "não aplicável", "0"]:
                        return None
                    partes = s.split('/')
                    if len(partes) == 3:
                        d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
                        today = datetime.date.today()
                        return today.year - a - ((today.month, today.day) < (m, d))
                    return None
                except:
                    return None

            c_membro_nasc = "Data Nascimento"
            c_membro_bat = "Batizado" # Coluna C
            c_conjuge_nasc = "Data Nascimento Cônjuge"
            c_conjuge_bat = "Batizado Cônjuge"
            colunas_filhos = [
                {"nasc": "Data Nascimento do Filho (a) - 1", "bat": "Batizado Filho 1"},
                {"nasc": "Data Nascimento do Filho (a) - 2", "bat": "Batizado Filho 2"},
                {"nasc": "Data Nascimento do Filho (a) - 3", "bat": "Batizado Filho 3"}
            ]

            lista_geral = []
            dados_planilha = df.to_dict('records')

            for row in dados_planilha:
                # 1. Processar Membro Principal
                m_idade = calcular_idade_manual(row.get(c_membro_nasc))
                if m_idade is not None:
                    bat_val = str(row.get(c_membro_bat, "Não")).strip().capitalize()
                    lista_geral.append({'Idade': m_idade, 'Batizado': bat_val, 'Tipo': 'Membro'})

                # 2. Processar Cônjuge
                c_idade = calcular_idade_manual(row.get(c_conjuge_nasc))
                if c_idade is not None:
                    # Lê o batismo real da coluna K
                    bat_c_val = str(row.get(c_conjuge_bat, "Não")).strip().capitalize()
                    if bat_c_val != "Não Aplicável":
                        lista_geral.append({'Idade': c_idade, 'Batizado': bat_c_val, 'Tipo': 'Cônjuge'})

                # 3. Processar Filhos
                for f_cols in colunas_filhos:
                    f_nasc = row.get(f_cols["nasc"])
                    f_idade = calcular_idade_manual(f_nasc)
                    if f_idade is not None:
                        # Lê o batismo real das colunas R, V ou Z
                        bat_f_val = str(row.get(f_cols["bat"], "Não")).strip().capitalize()
                        # Só adicionamos à estatística se o batismo for "Sim" ou "Não" 
                        # (Ignoramos "Não Aplicável" para não sujar o gráfico de batismo)
                        lista_geral.append({
                            'Idade': f_idade, 
                            'Batizado': bat_f_val if bat_f_val != "Não Aplicável" else "Não", 
                            'Tipo': 'Filho'
                        })

            df_total = pd.DataFrame(lista_geral)

            if not df_total.empty:
                # Agora que o df_total existe, podemos mostrar os números no topo
                total_membros = len(df) # Total de linhas (cadastros realizados)
                total_pessoas = len(df_total) # Total de indivíduos processados
                
                # Criando as colunas de destaque
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Total de Cadastros", f"{total_membros} 📝")
                with m2:
                    st.metric("Total de Pessoas", f"{total_pessoas} 👥")
                with m3:
                    agora = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
                    st.caption(f"**Última Atualização:**\n{agora}")
                
                st.divider()


            if df_total.empty:
                st.error("❌ Erro ao processar dados. Verifique os cabeçalhos da planilha.")
            else:

                st.subheader("👥 Distribuição por Faixa Etária")
                bins = [-1, 2, 7, 13, 18, 25, 35, 45, 60, 90, 130]
                labels = [
                    '👶 0-2 (Bebês)', '🎈 3-7 (Kids)', '🎒 8-13 (Juniores)', 
                    '🎸 14-18 (Adoles)', '🎓 19-25 (Jovens)', '👩‍💼 26-35 (Adultos J.)', 
                    '🏡 36-45 (Adultos)', '💼 46-60 (Maduros)', '👴 61-90 (Sênior)', '⭐️ > 90'
                ]
                df_total['Faixa'] = pd.cut(df_total['Idade'], bins=bins, labels=labels)
                contagem_idade = df_total['Faixa'].value_counts().reindex(labels, fill_value=0).reset_index()
                contagem_idade.columns = ['Faixa Etária', 'Quantidade']

                import altair as alt
                chart_idade = alt.Chart(contagem_idade).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color='#5271FF').encode(
                    x=alt.X('Faixa Etária', sort=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Quantidade', title='Nº de Pessoas'),
                    tooltip=['Faixa Etária', 'Quantidade']
                ).properties(height=350)
                st.altair_chart(chart_idade, use_container_width=True)

                st.divider()

                # --- GRÁFICO 2: PERCENTUAL DE BATIZADOS (Agora Real e Dinâmico) ---
                # Filtramos para a estatística de batismo apenas quem tem resposta "Sim" ou "Não"
                df_batismo = df_total[df_total['Batizado'].isin(["Sim", "Não"])].copy()
                
                if not df_batismo.empty:
                    col_meta, col_graph = st.columns([1, 2])
                    
                    stats = df_batismo['Batizado'].value_counts()
                    sim = stats.get("Sim", 0)
                    nao = stats.get("Não", 0)
                    total = len(df_batismo)
                    pct_sim = int((sim/total)*100) if total > 0 else 0

                    with col_meta:
                        st.subheader("💧 Batismo")
                        st.caption("Público Geral (Membros, Cônjuges e Filhos habilitados)")
                        st.metric("Pessoas Analisadas", total)
                        st.metric("Batizados (Sim)", sim, delta=f"{pct_sim}% do total", delta_color="normal")
                        st.metric("Não Batizados", nao)

                    with col_graph:
                        dados_bat = pd.DataFrame({'Status': ['Batizado', 'Não Batizado'], 'Qtd': [sim, nao]})
                        chart_bat = alt.Chart(dados_bat).mark_arc(innerRadius=65, outerRadius=110).encode(
                            theta=alt.Theta("Qtd", stack=True),
                            color=alt.Color("Status", scale=alt.Scale(domain=['Batizado', 'Não Batizado'], range=['#2ecc71', '#e74c3c'])),
                            tooltip=["Status", "Qtd"]
                        ).properties(title="Consolidado Espiritual")
                        st.altair_chart(chart_bat, use_container_width=True)
                
                # --- RODAPÉ ---
                st.divider()
