# Portal Web (Data Lake) — Ponto #1

Este é o primeiro bloco do fluxo "Processo Automatizado": o portal onde o
cliente carrega os ficheiros Excel/CSV, que ficam guardados numa estrutura
de pastas por cliente (o Data Lake) com um registo de auditoria em SQLite.

## Como correr

```bash
cd datalake_portal
pip install -r requirements.txt
streamlit run app.py
```

Isto abre o portal no browser (normalmente em http://localhost:8501).

## Credenciais de teste

| Cliente | Username | Password |
|---|---|---|
| Supermercado A | admin_a | teste123 |
| Supermercado B | admin_b | teste123 |

## O que acontece quando carregas um ficheiro

1. É validada a extensão (`.csv`, `.xlsx`, `.xls`).
2. O ficheiro é guardado em `data/<client_id>/<timestamp>_<nome_original>`.
3. É feita uma leitura de teste com `pandas` para confirmar que o ficheiro
   não está corrompido e contar as linhas.
4. O resultado (sucesso ou erro) fica registado em `db/registry.db`,
   na tabela `uploads`.

## Estrutura de pastas gerada

```
datalake_portal/
├── data/
│   ├── supermercado_a/
│   │   └── 20260827_143000_vendas_agosto.xlsx
│   └── supermercado_b/
├── db/
│   └── registry.db
├── clients.json
├── app.py
├── auth.py
├── db.py
├── add_client.py
└── requirements.txt
```

Isto **é** o Data Lake do teu fluxo: dados em bruto, tal como o cliente os
enviou, organizados por cliente e por data, prontos a ser lidos pelo ETL
(ponto #2).

## Adicionar novos clientes de teste

```bash
python add_client.py
```

## Ponto #2 — ETL e KPIs

O módulo `etl/` lê os ficheiros mais recentes de um cliente no Data Lake,
valida-os, limpa-os e calcula métricas de negócio, guardando tudo em
`db/analytics.db` (SQLite — placeholder da futura Base de Dados Cloud/Oracle).

### Correr o ETL

```bash
python -m etl.run_etl supermercado_a
```

### O que o ETL faz

1. **Extract** (`etl/extract.py`) — encontra o ficheiro de stock e o de vendas
   mais recentes na pasta `data/<client_id>/` (por nome do ficheiro).
2. **Validate** (`etl/validate.py`) — confirma colunas obrigatórias, valores
   negativos, códigos duplicados, preço abaixo do custo, e cruza
   "Unidades Vendidas" do stock com a soma das vendas diárias por produto
   (deteta inconsistências entre os dois ficheiros). Erros bloqueantes
   abortam o ETL; avisos são apenas registados.
3. **Transform** (`etl/transform.py`) — normaliza texto, tipos numéricos e
   remove duplicados.
4. **KPIs** (`etl/kpis.py`) — calcula:
   - **Por produto**: rotatividade semanal, cobertura de stock em dias,
     margem unitária (MT e %), valor de stock parado, estado
     (`OK` / `Alerta` / `Ruptura`).
   - **Por categoria**: vendas, margem bruta e margem %, nº de produtos.
   - **Diário**: vendas, margem, ticket médio, nº de produtos vendidos por dia.
   - **Resumo semanal**: melhor dia, produto mais vendido, produto mais
     rentável, produtos em risco de ruptura.
5. **Load** (`etl/load.py`) — grava tudo em `db/analytics.db`, e regista
   cada execução do ETL (sucesso/erro, avisos) na tabela `etl_runs`.

### Tabelas criadas em `db/analytics.db`

| Tabela | Conteúdo |
|---|---|
| `stock_produtos` | Dados de stock limpos |
| `vendas_diarias` | Dados de vendas limpos |
| `kpi_produto` | KPIs por produto |
| `kpi_categoria` | KPIs por categoria |
| `kpi_diario` | KPIs por dia |
| `kpi_resumo_semana` | Resumo executivo da semana (JSON) |
| `etl_runs` | Histórico de execuções do ETL |

## Ponto #3 — Base de Dados Oracle

O ETL agora suporta dois backends de gravação: **SQLite** (default, para
testes rápidos) e **Oracle**. O `run_etl.py` não muda nada — só a variável
`DB_BACKEND` decide qual motor é usado.

### 1. Preparar o Oracle

Como vais usar o schema/utilizador que já tens (não um dedicado), o único
passo é confirmar que não há colisão de nomes de tabelas antes de criar
o schema — o script de teste (passo 3) faz essa verificação por ti.

### 2. Configurar a ligação

Copia `oracle_config.example.json` para `oracle_config.json` e preenche
com o utilizador que já usas:

```json
{
  "user": "o_teu_utilizador",
  "password": "a_tua_password",
  "host": "o_teu_host",
  "port": 1521,
  "service_name": "o_teu_service_name"
}
```

Isto corresponde exatamente à tua função habitual (`oracledb.makedsn(host, port, service_name=...)`
seguido de `oracledb.connect(user=..., password=..., dsn=...)`) — o `load_oracle.py`
monta a ligação da mesma forma.

Alternativa (variáveis de ambiente, em vez do ficheiro JSON):
`ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_HOST`, `ORACLE_PORT`, `ORACLE_SERVICE_NAME`
(ou `ORACLE_DSN` se preferires passar o dsn já montado).

### 3. Testar a ligação e verificar colisões de nomes

```bash
set DB_BACKEND=oracle          # Windows (cmd)
$env:DB_BACKEND="oracle"       # Windows (PowerShell)
export DB_BACKEND=oracle       # Linux/Mac

python -m etl.test_oracle_connection
```

Este script liga-se e diz-te se algum dos nomes de tabela que o projeto
usa (`stock_produtos`, `kpi_produto`, etc.) já existe no teu schema. Se
já tiveres tabelas com esses nomes usadas para outra coisa, renomeia as
tabelas em `db/schema_oracle.sql` (e ajusta os nomes correspondentes em
`etl/run_etl.py` e na lista `REQUIRED_TABLES` de `etl/test_oracle_connection.py`)
antes de continuar — por exemplo, prefixando com `sm_`.

### 4. Criar as tabelas

Sem colisões, corre `db/schema_oracle.sql` no SQL Developer, ligado ao
teu utilizador habitual.

### 5. Correr o ETL a gravar no Oracle

Com `DB_BACKEND=oracle` definido (mesma sessão do terminal):

```bash
python -m etl.run_etl supermercado_a
```

Os dados passam a ser gravados nas tabelas Oracle em vez do `analytics.db`.
Podes confirmar no SQL Developer com `SELECT * FROM kpi_produto;`.

Para voltares ao SQLite (teste rápido, sem Oracle ligado), basta não
definires `DB_BACKEND` (ou pôr `DB_BACKEND=sqlite`).

### Como isto foi feito

- `etl/load_sqlite.py` — a implementação original (SQLite).
- `etl/load_oracle.py` — mesma interface, a gravar no Oracle via `python-oracledb`
  (modo *thin*, não precisa de instalar o Oracle Instant Client à parte).
- `etl/load.py` — só escolhe qual dos dois usar, consoante `config.DB_BACKEND`.
  O `run_etl.py` importa sempre `etl.load` e nunca precisa de saber qual
  motor está por trás.
- `db/schema_oracle.sql` — DDL para criar as tabelas no Oracle.

## Ponto #4 — Dashboard Web

O dashboard (`dashboard/app.py`, Streamlit) lê os KPIs já calculados pelo
ETL — nunca recalcula nada, só apresenta o que já está gravado na Base de
Dados. Usa o mesmo login (`clients.json`) do portal e o mesmo `DB_BACKEND`
configurado para o ETL (sqlite ou oracle).

### Correr

```bash
streamlit run dashboard/app.py
```

Se estiveres a usar Oracle, define `DB_BACKEND=oracle` (e as credenciais)
na mesma sessão do terminal antes de correres o comando, tal como fazes
para o ETL.

### O que mostra

- **Métricas principais**: vendas líquidas, margem bruta (valor e %),
  unidades vendidas, ticket médio, nº de produtos em risco.
- **Vendas por dia** (gráfico de linha) e **vendas/margem por categoria**
  (gráfico de barras).
- **Destaques da semana**: melhor dia, produto mais vendido, produto mais
  rentável.
- **Tabela de produtos** com o estado de stock (`OK` / `Alerta` / `Ruptura`)
  destacado a cores.
- **Histórico de execuções do ETL** (para diagnóstico).

### Como isto foi feito

- `etl/read.py` — camada de leitura, com o mesmo padrão de "router" do
  `etl/load.py`: escolhe o backend (sqlite/oracle) automaticamente a
  partir de `config.DB_BACKEND`, e nunca é preciso duplicar código entre
  os dois motores.
- `dashboard/app.py` — a interface Streamlit em si, reutilizando
  `auth.py` (login) e `etl/read.py` (dados).

## Notas para quando isto for para produção

- As passwords aqui usam apenas SHA-256 sem salt — suficiente para teste local,
  **não** para produção (usar bcrypt/argon2 e uma tabela na base de dados real).
- `clients.json` deveria passar a ser uma tabela na Base de Dados Cloud, não
  um ficheiro local.
- `oracle_config.json` fica de fora do controlo de versões (tem password em
  texto simples) — usa variáveis de ambiente ou um cofre de segredos em produção.
- Vais querer limites de tamanho de ficheiro e um antivírus/scan básico antes
  de aceitar uploads de clientes reais.
