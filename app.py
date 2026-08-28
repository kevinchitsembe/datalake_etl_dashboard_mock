"""
Portal Web (Data Lake) - Ponto #1 do fluxo "Processo Automatizado".

O cliente faz login, carrega ficheiros Excel/CSV, e estes são guardados
numa pasta própria (data/<client_id>/) com timestamp, simulando o Data Lake.
Cada upload fica registado em db/registry.db.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

import auth
import db

DATA_ROOT = Path(__file__).parent / "data"
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

st.set_page_config(page_title="Portal - Data Lake", page_icon="📥", layout="centered")
db.init_db()

if "client" not in st.session_state:
    st.session_state.client = None


def login_view():
    st.title("📥 Portal de Carregamento de Dados")
    st.caption("Faz login para carregar os teus ficheiros de vendas/stock.")

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


def portal_view():
    client = st.session_state.client
    client_id = client["client_id"]
    client_folder = DATA_ROOT / client_id
    client_folder.mkdir(parents=True, exist_ok=True)

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"📊 {client['name']}")
    with col2:
        if st.button("Sair"):
            st.session_state.client = None
            st.rerun()

    st.subheader("Carregar novo ficheiro")
    uploaded_file = st.file_uploader(
        "Excel ou CSV com dados de vendas/stock",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is not None:
        ext = Path(uploaded_file.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            st.error(f"Extensão '{ext}' não suportada.")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_name = f"{timestamp}_{uploaded_file.name}"
            saved_path = client_folder / saved_name

            with open(saved_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Validação básica: conseguimos ler o ficheiro e contar linhas?
            try:
                if ext == ".csv":
                    df = pd.read_csv(saved_path)
                else:
                    df = pd.read_excel(saved_path)
                rows = len(df)
                db.log_upload(client_id, uploaded_file.name, str(saved_path),
                               status="OK", rows_detected=rows)
                st.success(f"Ficheiro guardado com sucesso ({rows} linhas detetadas).")
                st.dataframe(df.head(10))
            except Exception as e:
                db.log_upload(client_id, uploaded_file.name, str(saved_path),
                               status="ERRO", message=str(e))
                st.error(f"Ficheiro guardado, mas não foi possível lê-lo: {e}")

    st.subheader("Histórico de carregamentos")
    uploads = db.get_uploads(client_id)
    if uploads:
        st.dataframe(pd.DataFrame(uploads)[
            ["upload_time", "filename", "status", "rows_detected", "message"]
        ])
    else:
        st.info("Ainda não há ficheiros carregados.")


if st.session_state.client is None:
    login_view()
else:
    portal_view()
