"""
Dashboard Web — Ponto #4 do fluxo "Processo Automatizado".

Lê os KPIs já calculados pelo ETL (ponto #2) na Base de Dados (ponto #3,
SQLite ou Oracle consoante DB_BACKEND) e mostra-os ao cliente.
Usa o mesmo login/clients.json do portal (ponto #1).

Correr com:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

import auth
from etl import read

st.set_page_config(page_title="Dashboard - KPIs", page_icon="📊", layout="wide")

if "client" not in st.session_state:
    st.session_state.client = None


def login_view():
    st.title("📊 Dashboard de Vendas e Stock")
    st.caption("Faz login para ver os KPIs do teu negócio.")

    with st.form("login_form"):
        username = st.text_input("Utilizador")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        client = auth.authenticate(username, password)
        if client:
            st.session_state.client = client
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

    with st.expander("Credenciais de teste"):
        st.code(
            "Cliente A -> utilizador: admin_a | password: teste123\n"
            "Cliente B -> utilizador: admin_b | password: teste123"
        )


def status_color(status: str) -> str:
    return {"Ruptura": "background-color: #ffcccc",
            "Alerta": "background-color: #fff3cd",
            "OK": "background-color: #d4edda"}.get(status, "")


def dashboard_view():
    client = st.session_state.client
    client_id = client["client_id"]

    col1, col2 = st.columns([5, 1])
    with col1:
        st.title(f"📊 {client['name']}")
    with col2:
        if st.button("Sair"):
            st.session_state.client = None
            st.rerun()

    if not read.has_data(client_id):
        st.warning(
            "Ainda não há dados processados para este cliente. "
            "Carrega ficheiros no portal e corre o ETL primeiro."
        )
        return

    resumo = read.get_resumo(client_id)
    df_produto = read.get_kpi_produto(client_id)
    df_categoria = read.get_kpi_categoria(client_id)
    df_diario = read.get_kpi_diario(client_id)

    st.caption(f"Período: {resumo['periodo_inicio']} a {resumo['periodo_fim']}")

    # --- Métricas principais ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Vendas líquidas", f"{resumo['vendas_liquidas_totais_mt']:,.0f} MT")
    m2.metric("Margem bruta", f"{resumo['margem_bruta_total_mt']:,.0f} MT",
              f"{resumo['margem_pct_total']*100:.1f}%")
    m3.metric("Unidades vendidas", f"{resumo['unidades_vendidas_totais']:,.0f}")
    m4.metric("Ticket médio", f"{resumo['ticket_medio_geral_mt']:.2f} MT")
    m5.metric("Produtos em risco", resumo["num_produtos_em_risco"])

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Vendas por dia")
        chart_diario = df_diario.set_index("data")[["vendas_liquidas_mt"]]
        st.line_chart(chart_diario)

    with col_b:
        st.subheader("Vendas por categoria")
        chart_categoria = df_categoria.set_index("categoria")[["vendas_liquidas_mt", "margem_bruta_mt"]]
        st.bar_chart(chart_categoria)

    st.divider()

    st.subheader("Destaques da semana")
    d1, d2, d3 = st.columns(3)
    d1.info(f"**Melhor dia:** {resumo['melhor_dia']}\n\n{resumo['melhor_dia_vendas_mt']:,.0f} MT em vendas")
    d2.success(f"**Mais vendido:** {resumo['produto_mais_vendido']}\n\n{resumo['produto_mais_vendido_unidades']} unidades")
    d3.success(f"**Mais rentável:** {resumo['produto_mais_rentavel']}\n\n{resumo['produto_mais_rentavel_margem_mt']:,.0f} MT de margem")

    if resumo["num_produtos_em_risco"] > 0:
        st.warning(f"⚠️ Produtos em risco de ruptura: {resumo['produtos_em_risco']}")

    st.divider()

    st.subheader("Produtos — detalhe")
    display_cols = [
        "produto", "categoria", "stock_final", "stock_minimo", "status_stock",
        "unidades_vendidas_semana", "vendas_liquidas_semana", "margem_bruta_semana",
        "cobertura_dias", "rotatividade_semanal",
    ]
    styler = df_produto[display_cols].style
    # Styler.applymap foi descontinuado a favor de .map em versões recentes do pandas;
    # tenta o novo nome primeiro e usa o antigo como fallback (compatibilidade).
    if hasattr(styler, "map"):
        styled = styler.map(status_color, subset=["status_stock"])
    else:
        styled = styler.applymap(status_color, subset=["status_stock"])
    st.dataframe(styled, width='stretch')

    with st.expander("Histórico de execuções do ETL"):
        st.dataframe(read.get_etl_runs(client_id), width='stretch')


if st.session_state.client is None:
    login_view()
else:
    dashboard_view()
