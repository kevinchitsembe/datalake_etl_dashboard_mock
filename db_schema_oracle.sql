-- ============================================================
-- Schema Oracle para o "Processo Automatizado" - Ponto #3
-- Corre este script no SQL Developer, ligado ao utilizador/schema
-- que vais usar para o ETL (ver README para criar esse utilizador).
-- ============================================================

CREATE TABLE stock_produtos (
    client_id             VARCHAR2(50)  NOT NULL,
    codigo_produto        VARCHAR2(20)  NOT NULL,
    produto               VARCHAR2(150),
    categoria             VARCHAR2(50),
    stock_inicial         NUMBER,
    entradas_semana       NUMBER,
    unidades_vendidas     NUMBER,
    stock_final           NUMBER,
    stock_minimo          NUMBER,
    reposicao_necessaria  NUMBER,
    preco_venda_mt        NUMBER(12,2),
    custo_unitario_mt     NUMBER(12,2)
);

CREATE TABLE vendas_diarias (
    client_id           VARCHAR2(50)  NOT NULL,
    data                DATE          NOT NULL,
    codigo_produto      VARCHAR2(20)  NOT NULL,
    produto             VARCHAR2(150),
    categoria           VARCHAR2(50),
    quantidade          NUMBER,
    preco_unitario_mt   NUMBER(12,2),
    vendas_liquidas_mt  NUMBER(12,2),
    custo_mt            NUMBER(12,2),
    margem_bruta_mt     NUMBER(12,2),
    desconto            NUMBER(12,2)
);

CREATE TABLE kpi_produto (
    client_id                 VARCHAR2(50)  NOT NULL,
    codigo_produto            VARCHAR2(20)  NOT NULL,
    produto                   VARCHAR2(150),
    categoria                 VARCHAR2(50),
    stock_inicial             NUMBER,
    entradas_semana           NUMBER,
    unidades_vendidas_semana  NUMBER,
    stock_final               NUMBER,
    stock_minimo              NUMBER,
    preco_venda_mt            NUMBER(12,2),
    custo_unitario_mt         NUMBER(12,2),
    vendas_liquidas_semana    NUMBER(12,2),
    margem_bruta_semana       NUMBER(12,2),
    desconto_total            NUMBER(12,2),
    rotatividade_semanal      NUMBER(10,4),
    cobertura_dias            NUMBER(10,2),
    margem_unitaria_mt        NUMBER(12,2),
    margem_unitaria_pct       NUMBER(6,4),
    valor_stock_final_mt      NUMBER(14,2),
    ticket_medio_unidade_mt   NUMBER(12,2),
    status_stock              VARCHAR2(20)
);

CREATE TABLE kpi_categoria (
    client_id           VARCHAR2(50) NOT NULL,
    categoria           VARCHAR2(50),
    unidades_vendidas   NUMBER,
    vendas_liquidas_mt  NUMBER(12,2),
    margem_bruta_mt     NUMBER(12,2),
    margem_pct          NUMBER(6,4),
    num_produtos        NUMBER
);

CREATE TABLE kpi_diario (
    client_id              VARCHAR2(50) NOT NULL,
    data                   VARCHAR2(20),
    unidades_vendidas      NUMBER,
    vendas_liquidas_mt     NUMBER(12,2),
    margem_bruta_mt        NUMBER(12,2),
    num_produtos_vendidos  NUMBER,
    ticket_medio_mt        NUMBER(12,2)
);

CREATE TABLE kpi_resumo_semana (
    client_id       VARCHAR2(50) NOT NULL,
    periodo_inicio  VARCHAR2(20) NOT NULL,
    periodo_fim     VARCHAR2(20) NOT NULL,
    data_json       CLOB,
    CONSTRAINT pk_kpi_resumo_semana PRIMARY KEY (client_id, periodo_inicio, periodo_fim)
);

CREATE TABLE etl_runs (
    id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id    VARCHAR2(50)  NOT NULL,
    run_time     TIMESTAMP,
    stock_file   VARCHAR2(400),
    sales_file   VARCHAR2(400),
    status       VARCHAR2(20),
    issues_json  CLOB
);

COMMIT;
