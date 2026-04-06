# --- IMPORTS ---
import streamlit as st
import pandas as pd
import requests, base64, re, datetime, unicodedata, time, io
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="IBPS Sumaré",
    page_icon="⛪",
    layout="wide"
)

# --- CONEXÃO COM PLANILHA ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES UTILITÁRIAS ---
def limpar_e_formatar_cpf(valor):
    if not valor or str(valor).lower() in ["nan", "none", ""]:
        return "Não Aplicável"
    limpo = re.sub(r'\D', '', str(valor).split('.')[0])
    if not limpo: return "Não Aplicável"
    c = limpo.zfill(11)
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

def limpar_rg(valor):
    if not valor or str(valor).lower() in ["nan", "none", ""]:
        return "Não Aplicável"
    return re.sub(r'\D', '', str(valor).split('.')[0])

def normalizar(texto):
    return "".join(c for c in unicodedata.normalize('NFD', str(texto))
                   if unicodedata.category(c) != 'Mn').lower().strip()

def tratar_campo(valor):
    if not valor or str(valor).lower() in ["nan", "none", "", "não aplicável"]:
        return "Não Aplicável"
    return valor

def calcular_idade(data_nasc):
    if not data_nasc: return 0
    today = datetime.date.today()
    return today.year - data_nasc.year - ((today.month, today.day) < (data_nasc.month, data_nasc.day))

def salvar_na_planilha(dados_nova_linha):
    try:
        df_atual = conn.read(ttl="10s")
        df_novo_registro = pd.DataFrame([dados_nova_linha], columns=df_atual.columns)
        df_final = pd.concat([df_atual, df_novo_registro], ignore_index=True)
        conn.update(data=df_final)
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")

def upload_document_github(member_name, file):
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = "viniciuscoimbraribeiro/cadastro-membros"
        branch = "main"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{timestamp}_{file.name.replace(' ', '_')}"
        member_folder = member_name.replace(' ', '_').upper()
        path = f"cadastros/{member_folder}/{file_name}"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        content = base64.b64encode(file.getvalue()).decode()
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        data = {"message": f"Doc: {member_name}", "content": content, "branch": branch}
        response = requests.put(url, json=data, headers=headers)
        if response.status_code in [200, 201]:
            return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        else:
            raise Exception(f"Erro GitHub: {response.json().get('message')}")
    except Exception as e:
        st.error(f"Erro no upload para GitHub: {e}")
        return "Não Anexado"
# --- ABA 1: CADASTRO ---
if aba == "📝 Novo Cadastro":
    st.markdown("<h1 style='text-align: center;'>Cadastro de Membros</h1>", unsafe_allow_html=True)

    # Mensagem de sucesso temporária
    if 'sucesso' in st.session_state:
        placeholder = st.empty()
        with placeholder.container():
            st.success("✅ Cadastro realizado com sucesso!")
        time.sleep(5)
        placeholder.empty()
        del st.session_state['sucesso']

    fid = st.session_state.get('form_id', 0)

    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome Completo", key=f"nome_{fid}")
        nascimento = st.date_input(
            "Data de Nascimento", 
            value=None, 
            format="DD/MM/YYYY", 
            min_value=datetime.date(1920, 1, 1), 
            max_value=datetime.date.today(), 
            key=f"nasc_{fid}"
        )
        endereco = st.text_input("Endereço Completo", key=f"end_{fid}")
        profissao = st.text_input("Profissão", key=f"prof_{fid}")

        rg_input = st.text_input("RG", key=f"rg_{fid}")
        rg_txt = limpar_rg(rg_input)

        cpf_input = st.text_input("CPF", key=f"cpf_{fid}", max_chars=11)
        cpf_txt = limpar_e_formatar_cpf(cpf_input)

    with col2:
        estado_civil = st.selectbox("Estado Civil", 
            ["Solteiro(a)", "Casado(a)", "União Estável", "Divorciado(a)", "Viúvo(a)"], 
            key=f"ec_{fid}"
        )
        nome_conjuge, dt_nasc_conjuge, prof_conjuge = "Não Aplicável", "Não Aplicável", "Não Aplicável"
        if estado_civil in ["Casado(a)", "União Estável"]:
            nome_conjuge = st.text_input("Nome do Cônjuge", key=f"nome_conj_{fid}")
            nasc_conj = st.date_input("Data Nascimento Cônjuge", value=None, 
                                      min_value=datetime.date(1900, 1, 1), 
                                      max_value=datetime.date.today(), 
                                      format="DD/MM/YYYY", key=f"nasc_conj_{fid}")
            dt_nasc_conjuge = nasc_conj.strftime("%d/%m/%Y") if nasc_conj else "Não Aplicável"
            prof_conjuge = st.text_input("Profissão do Cônjuge", key=f"prof_conj_{fid}")

        nome_mae = st.text_input("Nome da Mãe", key=f"mae_{fid}")
        nome_pai = st.text_input("Nome do Pai", key=f"pai_{fid}")

    # Filhos
    st.divider()
    st.subheader("👨‍👩‍👧‍👦 Filhos")
    tem_filhos = st.checkbox("Tem filhos?", key=f"has_kids_{fid}")
    filhos_dados = []

    if tem_filhos:
        qtd_filhos = st.number_input("Quantos filhos deseja cadastrar?", min_value=1, max_value=10, step=1)
        for i in range(qtd_filhos):
            c1, c2, c3 = st.columns([2, 1, 1])
            f_nome = c1.text_input(f"Nome Filho {i+1}", key=f"f{i+1}_nome_{fid}")
            f_nasc = c2.date_input(f"Nasc. Filho {i+1}", value=None, format="DD/MM/YYYY", 
                                   min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today(), 
                                   key=f"f{i+1}_nasc_{fid}")
            f_idade = calcular_idade(f_nasc) if f_nasc else 0
            c3.info(f"Idade: {f_idade}")
            filhos_dados.append([f_nome or "Não Aplicável", f_nasc.strftime("%d/%m/%Y") if f_nasc else "", f_idade])

    # Seção Igreja
    st.divider()
    st.subheader("⛪ Igreja")
    bat_membro = st.selectbox("O Membro é Batizado?", ["Selecione...", "Sim", "Não"], key=f"bat_mem_{fid}")
    bat_conjuge = "Não Aplicável"
    if estado_civil in ["Casado(a)", "União Estável"]:
        bat_conjuge = st.selectbox("Cônjuge é Batizado?", ["Selecione...", "Sim", "Não"], key=f"bat_conj_{fid}")
    pastor = st.selectbox("Pastor Responsável", ["Selecione...", "Adriano", "Albert", "Luis", "Não Aplicável"], key=f"pastor_{fid}")
    observacoes = st.text_area("Observações", key=f"obs_{fid}")
    documento_file = st.file_uploader("Anexar Documento", type=["pdf", "jpg", "png", "jpeg"], key=f"file_{fid}")

    if st.button("Salvar Cadastro"):
        if not nome or not nascimento or not nome_mae or not estado_civil:
            st.error("⚠️ Preencha os campos obrigatórios.")
        else:
            try:
                data_cadastro_stamp = datetime.datetime.now().strftime("%d/%m/%Y")
                link_final = upload_document_github(nome, documento_file) if documento_file else "Não Anexado"

                nova_linha = [
                    nome,
                    nascimento.strftime("%d/%m/%Y"),
                    bat_membro,
                    endereco,
                    profissao,
                    rg_txt,
                    cpf_txt,
                    nome_conjuge,
                    dt_nasc_conjuge,
                    prof_conjuge,
                    bat_conjuge,
                    nome_pai,
                    nome_mae,
                    estado_civil,
                    *(filhos_dados[i] if i < len(filhos_dados) else ["Não Aplicável", "", 0] for i in range(10)),
                    pastor,
                    observacoes or "Não Aplicável",
                    link_final,
                    data_cadastro_stamp
                ]

                salvar_na_planilha(nova_linha)
                st.session_state['sucesso'] = True
                st.session_state['form_id'] = fid + 1
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
# --- ABA 2: CONSULTA ---
elif aba == "🔍 Consulta":
    st.header("🔍 Consultar e Gerenciar Membros")

    # --- Autenticação ---
    if "autenticado_consulta" not in st.session_state:
        st.session_state.autenticado_consulta = False

    if not st.session_state.autenticado_consulta:
        senha_acesso = st.text_input("Digite a senha de administrador", type="password")
        if senha_acesso == st.secrets["ADMIN_PASS"]:
            st.session_state.autenticado_consulta = True
            st.rerun()
        elif senha_acesso:
            st.error("❌ Senha incorreta.")
        else:
            st.info("Aguardando senha para liberar o painel...")
        st.stop()

    if st.button("🔒 Bloquear Acesso"):
        st.session_state.autenticado_consulta = False
        st.rerun()

    # --- Funções auxiliares ---
    def renderizar_membro_completo(idx, df_contexto, sufixo):
        membro = df_contexto.loc[idx]
        nome_exibicao = str(membro['Nome Completo']).upper()

        val_cpf = limpar_e_formatar_cpf(membro['CPF'])
        val_rg = limpar_rg(membro['RG'])
        conjuge = tratar_campo(membro['Nome Completo Conjuge'])
        pai = tratar_campo(membro['Nome do Pai'])
        mae = tratar_campo(membro['Nome da Mãe'])

        with st.expander(f"👤 {nome_exibicao}"):
            edit_key = f"edit_mode_{idx}_{sufixo}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            if not st.session_state[edit_key]:
                # --- Modo visualização ---
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("### 📋 Dados")
                    st.write(f"**Nasc:** {membro['Data Nascimento']}")
                    st.write(f"**CPF:** {val_cpf}")
                    st.write(f"**RG:** {val_rg}")
                    st.write(f"**Profissão:** {tratar_campo(membro['Profissão'])}")

                with c2:
                    st.markdown("### 👨‍👩‍👧 Família")
                    st.write(f"**Estado Civil:** {tratar_campo(membro['Estado Civil'])}")
                    if conjuge != "Não Aplicável":
                        st.write(f"**Cônjuge:** {conjuge}")
                        st.write(f"🎂 Nasc. Cônjuge: {tratar_campo(membro['Data Nascimento Cônjuge'])}")
                        st.write(f"💼 Prof. Cônjuge: {tratar_campo(membro['Profissão Cônjuge'])}")
                    st.write(f"**Pai:** {pai}")
                    st.write(f"**Mãe:** {mae}")
                    st.write("**Filhos:**")
                    tem_filho = False
                    for i in range(1, 11):
                        f_nome = tratar_campo(membro.get(f'Nome do Filho (a) - {i}', "Não Aplicável"))
                        if f_nome != "Não Aplicável":
                            idade = membro.get(f'Idade do Filho(a) - {i}', 0)
                            bat_f = tratar_campo(membro.get(f'Batismo Filho {i}', "Não Aplicável"))
                            st.write(f"👶 {i}º: {f_nome} ({idade} anos) - Batizado: {bat_f}")
                            tem_filho = True
                    if not tem_filho:
                        st.caption("Nenhum filho registrado.")

                with c3:
                    st.markdown("### ⛪ Igreja")
                    st.write(f"**Batizado:** {membro['Batizado Membro']}")
                    st.write(f"**Pastor:** {membro['Pastor Responsável']}")
                    st.info(f"**Obs:** {tratar_campo(membro['Observações'])}")
                    doc_url = str(membro['Documentos'])
                    if "http" in doc_url:
                        st.link_button("📂 Ver Documento", doc_url, use_container_width=True)

                # --- Ações ---
                st.divider()
                col_pri, col_ed, col_ex = st.columns(3)
                if col_pri.button("🖨️ Imprimir Ficha", key=f"btn_prt_{idx}_{sufixo}"):
                    # Aqui você mantém o HTML de impressão que já tinha
                    st.toast("Preparando ficha...")

                if col_ed.button("📝 Editar Dados", key=f"btn_ed_{idx}_{sufixo}"):
                    st.session_state[edit_key] = True
                    st.rerun()

                if col_ex.button("🗑️ Excluir", key=f"btn_del_{idx}_{sufixo}"):
                    try:
                        df_drop = df_contexto.drop(idx)
                        conn.update(data=df_drop)
                        st.success("Excluído!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

            else:
                # --- Modo edição ---
                st.markdown(f"### 📝 Atualizar Cadastro: {membro['Nome Completo']}")
                st.caption("⚠️ Dados de RG e CPF são imutáveis.")
                # Aqui você mantém os blocos de edição que já tinha (nome, profissão, estado civil, cônjuge, filhos, igreja)
                # E no final, salva com conn.update(data=df_contexto)

# --- ABA 3: CATÁLOGO DE SERVIÇOS ---
elif aba == "🛠️ Catálogo":
    st.header("🛠️ Catálogo de Serviços e Profissões")
    st.write("Pesquise por profissionais dentro da nossa comunidade.")

    prof_busca = st.text_input("Digite a profissão que procura (Ex: Pedreiro, Advogado, Encanador...)")

    if st.button("🔎 Filtrar Profissionais", use_container_width=True):
        if prof_busca:
            try:
                df = conn.read(ttl="10s")
                encontrados = df[df['Profissão'].astype(str).str.contains(prof_busca, case=False, na=False)]

                if not encontrados.empty:
                    st.info(f"Encontramos {len(encontrados)} profissional(is):")
                    for _, row in encontrados.iterrows():
                        with st.container():
                            st.subheader(f"👤 {row['Nome Completo']}")
                            st.write(f"🛠️ **Especialidade:** {row['Profissão']}")
                            st.write("📞 **Contato:** Solicite à secretaria")
                            st.divider()
                else:
                    st.warning(f"Ainda não temos '{prof_busca}' cadastrado.")
            except Exception as e:
                st.error(f"Erro ao buscar profissionais: {e}")
        else:
            st.warning("Por favor, digite uma profissão para buscar.")

# --- ABA 4: ESTATÍSTICAS ---
elif aba == "📊 Estatísticas":
    st.header("📊 Painel Estatístico de Membros")
    st.write("Análise demográfica e espiritual consolidada da congregação.")

    with st.spinner("Processando indicadores..."):
        df = conn.read(ttl="5s")

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado. Cadastre membros para visualizar os gráficos.")
    else:
        # Função de cálculo de idade (usando lógica centralizada)
        def calcular_idade_manual(data_str):
            try:
                if not data_str or str(data_str).lower() in ["nan", "none", "", "não aplicável", "0"]:
                    return None
                partes = str(data_str).split('/')
                if len(partes) == 3:
                    d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
                    today = datetime.date.today()
                    return today.year - a - ((today.month, today.day) < (m, d))
                return None
            except:
                return None

        lista_geral = []
        dados_planilha = df.to_dict('records')

        for row in dados_planilha:
            # Membro principal
            m_idade = calcular_idade_manual(row.get("Data Nascimento"))
            if m_idade is not None:
                lista_geral.append({'Idade': m_idade, 'Batizado': str(row.get("Batizado Membro", "Não")), 'Tipo': 'Membro'})

            # Cônjuge
            c_idade = calcular_idade_manual(row.get("Data Nascimento Cônjuge"))
            if c_idade is not None:
                bat_c_val = str(row.get("Batizado Cônjuge", "Não"))
                if bat_c_val != "Não Aplicável":
                    lista_geral.append({'Idade': c_idade, 'Batizado': bat_c_val, 'Tipo': 'Cônjuge'})

            # Filhos (até 10)
            for i in range(1, 11):
                f_nasc = row.get(f"Data Nascimento do Filho (a) - {i}")
                f_idade = calcular_idade_manual(f_nasc)
                if f_idade is not None:
                    bat_f_val = str(row.get(f"Batismo Filho {i}", "Não"))
                    if bat_f_val != "Não Aplicável":
                        lista_geral.append({'Idade': f_idade, 'Batizado': bat_f_val, 'Tipo': 'Filho'})

        df_total = pd.DataFrame(lista_geral)

        if not df_total.empty:
            total_membros = len(df)
            total_pessoas = len(df_total)

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total de Cadastros", f"{total_membros} 📝")
            with m2:
                st.metric("Total de Pessoas", f"{total_pessoas} 👥")
            with m3:
                agora = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
                st.caption(f"**Última Atualização:** {agora}")

            st.divider()

            # Distribuição por faixa etária
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

            chart_idade = alt.Chart(contagem_idade).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color='#5271FF').encode(
                x=alt.X('Faixa Etária', sort=None, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Quantidade', title='Nº de Pessoas'),
                tooltip=['Faixa Etária', 'Quantidade']
            ).properties(height=350)
            st.altair_chart(chart_idade, use_container_width=True)

            st.divider()

            # Percentual de batizados
            st.subheader("💧 Batismo")
            df_batismo = df_total[df_total['Batizado'].isin(["Sim", "Não"])].copy()
            if not df_batismo.empty:
                col_meta, col_graph = st.columns([1, 2])
                stats = df_batismo['Batizado'].value_counts()
                sim = stats.get("Sim", 0)
                nao = stats.get("Não", 0)
                total = len(df_batismo)
                pct_sim = int((sim/total)*100) if total > 0 else 0

                with col_meta:
                    st.caption("Público Geral (Membros, Cônjuges e Filhos habilitados)")
                    st.metric("Pessoas Analisadas", total)
                    st.metric("Batizados (Sim)", sim, delta=f"{pct_sim}% do total")
                    st.metric("Não Batizados", nao)

                with col_graph:
                    dados_bat = pd.DataFrame({'Status': ['Batizado', 'Não Batizado'], 'Qtd': [sim, nao]})
                    chart_bat = alt.Chart(dados_bat).mark_arc(innerRadius=65, outerRadius=110).encode(
                        theta=alt.Theta("Qtd", stack=True),
                        color=alt.Color("Status", scale=alt.Scale(domain=['Batizado', 'Não Batizado'], range=['#2ecc71', '#e74c3c'])),
                        tooltip=["Status", "Qtd"]
                    ).properties(title="Consolidado Espiritual")
                    st.altair_chart(chart_bat, use_container_width=True)

        else:
            st.error("❌ Erro ao processar dados. Verifique os cabeçalhos da planilha.")
