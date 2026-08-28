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

Quando migrarmos para Oracle (ponto #3), só o `etl/load.py` (e o
`config.ANALYTICS_DB_PATH`) precisam de mudar — o resto do pipeline mantém-se.

## Notas para quando isto for para produção

- As passwords aqui usam apenas SHA-256 sem salt — suficiente para teste local,
  **não** para produção (usar bcrypt/argon2 e uma tabela na base de dados real).
- `clients.json` deveria passar a ser uma tabela na Base de Dados Cloud, não
  um ficheiro local.
- Vais querer limites de tamanho de ficheiro e um antivírus/scan básico antes
  de aceitar uploads de clientes reais.
