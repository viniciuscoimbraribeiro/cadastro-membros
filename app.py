import streamlit as st
import pandas as pd
import requests
import base64
import re
import datetime
from streamlit_gsheets import GSheetsConnection
import unicodedata
import streamlit.components.v1 as components

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

def calcular_idade(data_nasc):
    if not data_nasc: return 0
    today = date.today()
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
    #with col_l2:
     #   try:
     #       st.image("logo_igreja.png", use_container_width=True)
     #   except:
     #       st.warning("Logo não encontrado.")

    st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)
    
    if 'sucesso' in st.session_state:
        st.success("✅ Cadastro realizado com sucesso!")
        del st.session_state['sucesso']

    fid = st.session_state['form_id']
    
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome Completo", key=f"nome_{fid}")
        #nascimento = ("Data de Nascimento (DD/MM/AAAA)", value=None, format="DD/MM/YYYY", min_value=date(1920, 1, 1), key=f"nasc_{fid}") 
        # Faltou o st.date_input antes do parênteses!
        nascimento = st.date_input(
            "Data de Nascimento (DD/MM/AAAA)", 
            value=None, 
            format="DD/MM/YYYY", 
            min_value=datetime.date(1920, 1, 1), 
            max_value=datetime.date.today(),
            key=f"nasc_{fid}"
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
        
        # 1. Inicializamos as variáveis padrão (caso não entre no IF)
        nome_conjuge = "Não Aplicável"
        dt_nasc_conjuge = "Não Aplicável"
        prof_conjuge = "Não Aplicável"
    
        # 2. Se for casado ou união estável, EXIBE os campos para preenchimento
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
            # Adicionei "_volat" ou qualquer termo para diferenciar de outros campos
            prof_conjuge = st.text_input("Profissão do Cônjuge", key=f"prof_conj_input_extra_{fid}")     
            
            # Calendário para o cônjuge
            #data_obj_conj = st.date_input("Data Nascimento Cônjuge", format="DD/MM/YYYY", key=f"dt_calend_conj_{fid}")
            #dt_nasc_conjuge = data_obj_conj.strftime("%d/%m/%Y")
            #prof_conjuge = st.text_input("Profissão do Cônjuge", key=f"prof_conj_input_{fid}")
    
        # 3. Campos que SEMPRE aparecem (Pai e Mãe) - Fora do IF
        nome_mae = st.text_input("Nome da Mãe", key=f"mae_{fid}")
        nome_pai = st.text_input("Nome do Pai", key=f"pai_{fid}")




    
    st.divider()
    st.subheader("👨‍👩‍👧‍👦 Filhos")
    tem_filhos = st.checkbox("Tem filhos?", key=f"has_kids_{fid}")
    filhos_dados = [["Não Aplicável", "", 0] for _ in range(3)]
    
    if tem_filhos:
        for i in range(3):
            if i == 0 or st.checkbox(f"Adicionar Filho(a) {i+1}?", key=f"chk_f{i+1}_{fid}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                f_nome = c1.text_input(f"Nome Filho {i+1}", key=f"f{i+1}n_{fid}")
                #f_nasc = c2.date_input(f"Nasc. Filho {i+1} (DD/MM/AAAA)", value=None,format="DD/MM/YYYY", help="DD/MM/AAAA", key=f"f{i+1}d_{fid}")
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
                if f_nome: filhos_dados[i] = [f_nome, f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade]

    st.divider()
    st.subheader("⛪ Igreja")
    batizado = st.selectbox("Batizado", ["Sim", "Não"], key=f"bat_{fid}")
    pastor = st.selectbox("Pastor Responsável", ["Adriano", "Albert", "Luis", "Não Aplicável"], key=f"past_{fid}")
    
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
                    nome_conjuge, dt_nasc_conjuge, prof_conjuge,
                    nome_pai, nome_mae, estado_civil,
                    filhos_dados[0][0], filhos_dados[0][1], filhos_dados[0][2],
                    filhos_dados[1][0], filhos_dados[1][1], filhos_dados[1][2],
                    filhos_dados[2][0], filhos_dados[2][1], filhos_dados[2][2],
                    batizado, pastor, observacoes or "Não Aplicável", link_final
                ]

                salvar_na_planilha(nova_linha)
                st.session_state['sucesso'] = True
                st.session_state['form_id'] += 1
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
                pass 
elif aba == "🔍 Consulta de Membros":

    # 1. Inicializar o estado de autenticação se não existir
    if "autenticado_consulta" not in st.session_state:
        st.session_state.autenticado_consulta = False

    # 2. Se NÃO estiver autenticado, mostra o campo de senha
    if not st.session_state.autenticado_consulta:
        senha_acesso = st.text_input("Digite a senha para acessar a consulta", type="password", key="senha_admin")
        
        if senha_acesso == "1234": # Substitua pela sua senha
            st.session_state.autenticado_consulta = True
            st.rerun() # Recarrega para sumir com o campo de senha imediatamente
        elif senha_acesso != "":
            st.error("❌ Senha incorreta.")
        else:
            st.info("Aguardando senha para liberar o painel...")

    # 3. Se ESTIVER autenticado, mostra apenas o conteúdo da consulta
    else:
        # Botão opcional para "Sair" ou bloquear novamente
        if st.button("🔒 Bloquear Acesso"):
            st.session_state.autenticado_consulta = False
            st.rerun()
            
            
        st.header("🔍 Consultar e Gerenciar Membros")
        
        nome_busca = st.text_input("Digite o nome para pesquisar", key="input_busca")
        botao_buscar = st.button("🔎 Buscar por Membro", key="btn_busca_membros", use_container_width=True)
        
        # A busca acontece se apertar ENTER (nome_busca) OU se clicar no BOTÃO (botao_buscar)
        if nome_busca or botao_buscar:
            try:
                # Forçamos a leitura sem cache para garantir dados frescos
                df = conn.read(ttl="10s")
                
                def normalizar(texto):
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
                                    import re
    
                                    # --- LIMPEZA DO CPF ---
                                    # Converte para string e remove espaços
                                    val_cpf = str(linha[5]).strip()
                                
                                    # Se o Pandas trouxe o .0, nós cortamos
                                    if val_cpf.endswith('.0'):
                                        val_cpf = val_cpf[:-2]
                                
                                    # Mantém apenas os números
                                    cpf_limpo = re.sub(r'\D', '', val_cpf)
                                
                                    if len(cpf_limpo) >= 1:
                                        # Preenche com zero à esquerda até ter 11 dígitos
                                        c = cpf_limpo.zfill(11)
                                        cpf_f = f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
                                    else:
                                        cpf_f = "Não Aplicável"
    
                                    # --- LIMPEZA DO RG ---
                                    val_rg = str(linha[4]).strip()
                                    if val_rg.endswith('.0'):
                                        val_rg = val_rg[:-2]
                                    rg_f = re.sub(r'\D', '', val_rg)
                                    if not rg_f:
                                        rg_f = "Não Aplicável"
    
                                    # --- EXIBIÇÃO ---
                                    st.write(f"**Nasc:** {linha[1]}")
                                    st.write(f"**CPF:** {cpf_f}")
                                    st.write(f"**RG:** {rg_f}")
                                    st.write(f"**Profissão:** {linha[3]}")
                                
                                with c2:
                                    st.markdown("### 👨‍👩‍👧 Família")
                                    
                                   # Função rápida para tratar campos vazios ou 'nan' (comum em planilhas)
                                    def tratar_campo(valor):
                                        if not valor or str(valor).lower() in ["nan", "none", ""]:
                                            return "Não Aplicável"
                                        return valor
                                    
                                    # Cônjuge com tratamento para vazio
                                    #conjuge = linha[6] if str(linha[6]).strip() and str(linha[6]) != "nan" else "Não Aplicável"
                                    #st.write(f"**Cônjuge:** {conjuge}")
    
                                    conjuge = tratar_campo(linha[6])
                                    if conjuge != "Não Aplicável":
                                        st.write(f"**Cônjuge:** {conjuge}")
                                        
                                        # Novos campos nas colunas 7 e 8
                                        dt_nasc_conjuge = tratar_campo(linha[7])
                                        prof_conjuge = tratar_campo(linha[8])
                                        
                                        if dt_nasc_conjuge != "Não Aplicável":
                                            st.write(f"🎂 **Nascimento Cônjuge:** {dt_nasc_conjuge}")
                                        
                                        if prof_conjuge != "Não Aplicável":
                                            st.write(f"💼 **Profissão Cônjuge:** {prof_conjuge}")
                                    else:
                                        st.write("**Cônjuge:** Não Aplicável")
                                        
                                    st.write(f"**Pai:** {tratar_campo(linha[9])}")
                                    st.write(f"**Mãe:** {tratar_campo(linha[10])}")
                                    st.write(f"**Estado Civil:** {tratar_campo(linha[11])}")
                                    
                                    # --- EXIBIÇÃO DOS FILHOS (OCULTA SE VAZIO OU NÃO APLICÁVEL) ---
                                    st.write("**Lista de Filhos:**")
                                    
                                    f1_nome = tratar_campo(linha[12])
                                    if f1_nome != "Não Aplicável":
                                        f1_idade = linha[14]
                                        st.write(f"👶 **1º:** {f1_nome} ({f1_idade} anos)")
                                    
                                    f2_nome = tratar_campo(linha[15])
                                    if f2_nome != "Não Aplicável":
                                        f2_idade = linha[17]
                                        st.write(f"👶 **2º:** {f2_nome} ({f2_idade} anos)")
                                    
                                    f3_nome = tratar_campo(linha[18])
                                    if f3_nome != "Não Aplicável":
                                        f3_idade = linha[20]
                                        st.write(f"👶 **3º:** {f3_nome} ({f3_idade} anos)")
                                    
                                    # Opcional: Se nenhum dos três existir, você pode mostrar um aviso
                                    if all(tratar_campo(linha[i]) == "Não Aplicável" for i in [12, 15, 18]):
                                        st.caption("Nenhum filho registrado.")
                                with c3:
                                    st.markdown("### ⛪ Igreja")
                                    st.write(f"**Batizado:** {linha[21]}") # Era Pastor, agora é Batizado
                                    st.write(f"**Pastor:** {linha[22]}")   # Era Obs, agora é Pastor
                                    st.info(f"**Obs:** {linha[23]}")       # Era link, agora é Obs
                                if len(linha) > 24 and "http" in str(linha[24]):
                                    st.link_button("📂 Visualizar Documento", linha[24], use_container_width=True)
    
                                st.divider()
                                col_pri, col_ed, col_ex = st.columns(3)
                                
                                # 1. BOTÃO IMPRIMIR (Restaurado)
                                if col_pri.button("🖨️ Imprimir", key=f"btn_prt_{idx}"):
                                    # Preparando os dados dos filhos para o HTML (Colunas 10, 13 e 16 são os nomes)
                                    filhos_html = ""
                                    for i in [10, 13, 16]:
                                        nome_filho = str(linha[i]).strip()
                                        if nome_filho and nome_filho.lower() != "não aplicável" and nome_filho != "nan":
                                            idade_filho = linha[i+2]
                                            filhos_html += f"<li>{nome_filho} ({idade_filho} anos)</li>"
                                    
                                    if not filhos_html:
                                        filhos_html = "<li>Nenhum filho registrado</li>"
                                
                                    html_print = f"""
                                    <script>
                                        var win = window.open('', '_blank');
                                        win.document.write('<html><head><title>Ficha de Membro</title>');
                                        win.document.write('<style>body {{ font-family: sans-serif; padding: 20px; line-height: 1.6; }}');
                                        win.document.write('h2 {{ text-align: center; color: #333; border-bottom: 2px solid #333; }}');
                                        win.document.write('.section {{ margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; }}');
                                        win.document.write('.title {{ font-weight: bold; background: #f4f4f4; padding: 5px; display: block; margin-bottom: 10px; }}');
                                        win.document.write('p {{ margin: 5px 0; }} b {{ color: #555; }}');
                                        win.document.write('</style></head><body>');
                                        
                                        win.document.write('<h2>FICHA CADASTRAL DE MEMBRO</h2>');
                                
                                        // SEÇÃO 1: DADOS PESSOAIS
                                        win.document.write('<div class="section"><span class="title">I. DADOS PESSOAIS</span>');
                                        win.document.write('<p><b>Nome Completo:</b> {linha[0]}</p>');
                                        win.document.write('<p><b>Data de Nascimento:</b> {linha[1]}</p>');
                                        win.document.write('<p><b>Endereço:</b> {linha[2]}</p>');
                                        win.document.write('<p><b>Profissão:</b> {linha[3]}</p>');
                                        win.document.write('<p><b>RG:</b> {linha[4]} &nbsp;&nbsp;&nbsp; <b>CPF:</b> {linha[5]}</p>');
                                        win.document.write('<p><b>Estado Civil:</b> {linha[9]}</p></div>');
                                
                                        // SEÇÃO 2: FAMÍLIA
                                        win.document.write('<div class="section"><span class="title">II. FAMÍLIA</span>');
                                        win.document.write('<p><b>Cônjuge:</b> {linha[6]}</p>');
                                        win.document.write('<p><b>Pai:</b> {linha[7]}</p>');
                                        win.document.write('<p><b>Mãe:</b> {linha[8]}</p>');
                                        win.document.write('<p><b>Filhos:</b></p><ul>' + `{filhos_html}` + '</ul></div>');
                                
                                        // SEÇÃO 3: IGREJA E OBSERVAÇÕES
                                        win.document.write('<div class="section"><span class="title">III. REGISTRO ECLESIÁSTICO</span>');
                                        win.document.write('<p><b>Batizado:</b> {linha[19]}</p>');
                                        win.document.write('<p><b>Pastor Responsável:</b> {linha[20]}</p>');
                                        win.document.write('<p><b>Observações:</b> {linha[21]}</p></div>');
                                
                                        win.document.write('<footer style="text-align:center; font-size: 10px; margin-top: 50px;">Gerado em: ' + new Date().toLocaleString() + '</footer>');
                                        win.document.write('</body></html>');
                                        win.document.close();
                                        
                                        // Pequeno delay para garantir que o estilo carregue antes de abrir a caixa de impressão
                                        setTimeout(function() {{ win.print(); }}, 500);
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
                                    
                                    # 1. LIMPEZA DO CPF PARA O CAMPO DE TEXTO
                                    import re
                                    raw_cpf_edit = str(linha[5]).strip()
                                    if raw_cpf_edit.endswith('.0'):
                                        raw_cpf_edit = raw_cpf_edit[:-2]
                                    cpf_limpo_edit = re.sub(r'\D', '', raw_cpf_edit)
                                    # 2. LÓGICA DO ESTADO CIVIL
                                    opcoes_civil = ["Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)"]
                                    try:
                                        # Procura a posição do texto que está na planilha dentro da nossa lista
                                        idx_civil = opcoes_civil.index(str(linha[9]).strip())
                                    except:
                                        # Se der erro (ex: campo vazio), assume o primeiro da lista
                                        idx_civil = 0
    
                                    with col_e1:
                                        n_nome = st.text_input("Nome", value=linha[0])
                                        
                                        # Tratamento de Data
                                        try:
                                            data_dt = pd.to_datetime(linha[1], dayfirst=True).date()
                                        except:
                                            from datetime import date
                                            data_dt = date.today()
                                        
                                        n_nasc = st.date_input("Nascimento", value=data_dt, format="DD/MM/YYYY")
                                        n_end = st.text_input("Endereço", value=linha[2])
                                        # CPF LIMPO AQUI:
                                        n_cpf = st.text_input("CPF", value=cpf_limpo_edit)
    
                                    with col_e2:
                                        n_estado_civil = st.selectbox("Estado Civil", opcoes_civil, index=idx_civil)
                                        n_conj = st.text_input("Cônjuge", value=linha[6])
                                        n_batizado = st.selectbox("Batizado", ["Sim", "Não"], index=0 if str(linha[19]) == "Sim" else 1)
                                        opcoes_pastor = ["Adriano", "Albert", "Luis", "Não Aplicável"]
                                        
                                        # Tenta encontrar o índice, se não achar, usa o padrão (índice 3)
                                        pastor_atual = str(linha[20]).strip()
                                        idx_pastor = opcoes_pastor.index(pastor_atual) if pastor_atual in opcoes_pastor else 3
                                        
                                        n_pastor = st.selectbox("Pastor Responsável", opcoes_pastor, index=idx_pastor)
                                        n_obs = st.text_area("Observações", value=linha[21])
                                    
                                    # BOTÕES COM KEYS ÚNICAS
                                    c_save, c_cancel = st.columns(2)
                                    btn_salvar = c_save.form_submit_button("💾 Salvar Alterações")
                                    btn_cancelar = c_cancel.form_submit_button("❌ Cancelar", key=f"btn_canc_{idx}")
    
                                    if btn_salvar:
                                        # Limpeza final do CPF antes de salvar na planilha
                                        cpf_final = re.sub(r'\D', '', n_cpf)
                                        
                                        df.at[idx, df.columns[0]] = n_nome
                                        df.at[idx, df.columns[1]] = n_nasc.strftime('%d/%m/%Y')
                                        df.at[idx, df.columns[2]] = n_end
                                        df.at[idx, df.columns[5]] = cpf_final
                                        df.at[idx, df.columns[6]] = n_conj
                                        df.at[idx, df.columns[9]] = n_estado_civil
                                        df.at[idx, df.columns[19]] = n_batizado
                                        df.at[idx, df.columns[20]] = n_pastor
                                        df.at[idx, df.columns[21]] = n_obs
                                        
                                        try:
                                            conn.update(data=df)
                                            st.success("Dados atualizados!")
                                            st.session_state[edit_key] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error("Erro ao salvar no Google. Tente novamente em instantes.")
                                    
                                    if btn_cancelar:
                                        st.session_state[edit_key] = False
                                        st.rerun()
                                    
    
                else:
                    st.warning("Nenhum membro encontrado.")
            except Exception as e:
                st.error(f"Erro: {e}")
            pass                            

            
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
    st.write("Análise demográfica e espiritual da congregação.")

    # 1. Carregamento de Dados com Cache Curto (para ser dinâmico)
    with st.spinner("Processando indicadores..."):
        df = conn.read(ttl="1s")

    if df.empty:
        st.warning("⚠️ Nenhuns dados encontrados. Cadastre membros para visualizar os gráficos.")
    else:
        # --- TRATAMENTO DE DADOS (Back-end) ---
        def calcular_idade(nascimento):
            try:
                if not nascimento or str(nascimento).lower() in ["nan", "none", ""]:
                    return None
                data_nasc = pd.to_datetime(nascimento, dayfirst=True).date()
                today = date.today()
                return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))
            except:
                return None

        # Criamos colunas auxiliares para o cálculo
        # Coluna 1 = Data de Nascimento
        # Coluna 21 = Batizado (Sim/Não)
        df['Idade_Calculada'] = df.iloc[:, 1].apply(calcular_idade)
        df_valido = df.dropna(subset=['Idade_Calculada'])

        # --- SEÇÃO 1: FAIXA ETÁRIA ---
        st.subheader("👥 Distribuição por Faixa Etária")
        
        # Definição dos Buckets conforme sua solicitação
        bins = [0, 2, 7, 13, 18, 25, 35, 45, 60, 90, 130]
        labels = [
            '👶 0-2 (Bebês)', '🎈 3-7 (Kids)', '🎒 8-13 (Juniores)', 
            '🎸 14-18 (Adoles)', '🎓 19-25 (Jovens)', '👩‍💼 26-35 (Adultos J.)', 
            '🏡 36-45 (Adultos)', '💼 46-60 (Maduros)', '👴 61-90 (Sênior)', '⭐️ > 90'
        ]

        df_valido['Faixa'] = pd.cut(df_valido['Idade_Calculada'], bins=bins, labels=labels, right=True)
        contagem_idade = df_valido['Faixa'].value_counts().reindex(labels, fill_value=0).reset_index()
        contagem_idade.columns = ['Faixa Etária', 'Quantidade']

        # Gráfico de Barras Estilizado (Altair)
        import altair as alt
        chart_idade = alt.Chart(contagem_idade).mark_bar(
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5,
            color='#5271FF' # Azul padrão profissional
        ).encode(
            x=alt.X('Faixa Etária', sort=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Quantidade', title='Nº de Membros'),
            tooltip=['Faixa Etária', 'Quantidade']
        ).properties(height=350)

        st.altair_chart(chart_idade, use_container_width=True)

        st.divider()

        # --- SEÇÃO 2: BATISMO (REGRA: APENAS >= 18 ANOS) ---
        col_meta, col_graph = st.columns([1, 2])

        # Filtrando apenas adultos para a estatística de batismo
        df_adultos = df_valido[df_valido['Idade_Calculada'] >= 18]
        status_batismo = df_adultos.iloc[:, 21].astype(str).str.strip().value_counts()
        
        sim = status_batismo.get("Sim", 0)
        nao = status_batismo.get("Não", 0)
        total_adultos = len(df_adultos)

        with col_meta:
            st.subheader("💧 Batismo")
            st.caption("Apenas membros ≥ 18 anos")
            st.metric("Total Adultos", total_adultos)
            st.metric("Batizados", sim, delta=f"{int((sim/total_adultos)*100) if total_adultos > 0 else 0}%", delta_color="normal")
            st.metric("Não Batizados", nao)

        with col_graph:
            if total_adultos > 0:
                dados_bat = pd.DataFrame({
                    'Status': ['Batizado', 'Não Batizado'],
                    'Qtd': [sim, nao]
                })
                
                chart_bat = alt.Chart(dados_bat).mark_arc(innerRadius=65, outerRadius=110).encode(
                    theta=alt.Theta("Qtd", stack=True),
                    color=alt.Color("Status", scale=alt.Scale(domain=['Batizado', 'Não Batizado'], range=['#2ecc71', '#e74c3c'])),
                    tooltip=["Status", "Qtd"]
                ).properties(title="Proporção de Batismo (Público Adulto)")
                
                st.altair_chart(chart_bat, use_container_width=True)
            else:
                st.info("Ainda não há adultos cadastrados para gerar o gráfico de batismo.")

        # --- RODAPÉ ---
        st.divider()
        atualizacao = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        st.caption(f"Estatísticas geradas automaticamente em {atualizacao}. Total de registros analisados: {len(df)}")
