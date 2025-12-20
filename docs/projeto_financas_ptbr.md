# Documento do Projeto – App de Finanças Pessoais

## 1. Visão geral

O **App de Finanças Pessoais** é uma aplicação web (Python + Streamlit) para controlar finanças e investimentos de forma integrada, acessível via navegador em desktop e celular.

### 1.1. Objetivos principais

- Consolidar receitas, despesas, saldos de contas e patrimônio investido em uma única visão, com filtros por mês, ano e todo o histórico.  
- Calcular automaticamente quanto investir a cada mês, com base na receita e em percentuais/valores definidos pelo usuário para diferentes objetivos (longo prazo, médio prazo, viagens, curto prazo, pets, cripto etc.).  
- Monitorar a alocação alvo da carteira por classe de ativo (ex.: 60% ações, 30% ETFs, 10% cripto) e sugerir rebalanceamento quando houver desvios relevantes.  

### 1.2. Usuários e contexto

- Usuários principais: o autor do projeto e sua esposa, compartilhando uma visão conjunta das finanças.  
- Futuro: possibilidade de abrir para amigos, cada um com sua própria conta e dados isolados.  
- Uso: acesso online com custo zero ou muito baixo, preferencialmente via Streamlit Community Cloud conectado ao GitHub.  

## 2. Escopo do MVP

O MVP foca em algumas funcionalidades essenciais:

### 2.1. Coleta de dados (mensal, via pasta)

- Leitura mensal de extratos e notas de diferentes instituições a partir de arquivos colocados em uma pasta configurada.  
- Instituições contempladas no MVP: ABN (contas), Revolut (conta), AMEX (cartão de crédito), Coinbase (cripto) e XP Investimentos (renda variável / renda fixa).  

### 2.2. Modelo de dados unificado

- Padronizar todas as fontes em um modelo único de transações com campos: data, descrição, conta/origem, tipo de transação, categoria, subcategoria, valor, moeda, ativo, classe de ativo.  

### 2.3. Orçamento e regras de investimento mensal

- Configurar, via interface, o percentual da receita mensal destinado a investimentos (ex.: 50%) e a divisão interna entre objetivos/“caixinhas” (longo prazo, médio prazo, valor fixo para viagens etc.).  
- Calcular automaticamente os aportes recomendados em cada objetivo para o período selecionado.  

### 2.4. Monitor de carteira e alocação alvo

- Definir, via interface, a alocação alvo por classe de ativo (ex.: 60% ações, 30% ETFs, 10% cripto).  
- Calcular a alocação atual da carteira e comparar alvo vs. atual, com alertas de desvio e sugestão de rebalanceamento.  

### 2.5. Visualizações básicas

- Gráfico de fluxo de caixa (receitas x despesas) por mês.  
- Gráfico de evolução do patrimônio na moeda base.  
- Gráfico de alocação alvo vs. atual por classe de ativo.  

### 2.6. Segurança básica

- Autenticação por usuário/senha antes de exibir qualquer dado financeiro.  
- Código público no GitHub, mas dados reais, configurações sensíveis e segredos mantidos fora do repositório, usando arquivos ignorados e armazenamento seguro de segredos.  

## 3. Requisitos funcionais

### F1 – Upload e ingestão de dados

- O sistema deve ler arquivos colocados em uma pasta configurada (ex.: `data/real/abn`, `data/real/xp`) em base mensal.  
- O sistema deve suportar, no MVP, arquivos de ABN, Revolut, AMEX, Coinbase e XP Investimentos.  
- Para cada instituição, o sistema deve implementar um “loader” específico que converta o layout original para o modelo interno de transações.  

### F2 – Modelo unificado de transações

Cada transação deve conter, no mínimo:

- `id_transacao`  
- `data`  
- `descricao`  
- `conta_origem` / `instituicao`  
- `tipo_movimento` (Income, Expense, Transfer, Contribution, Withdrawal, Adjustment)
  - **Income**: entradas de dinheiro vindas de fora (salário, restituições, dividendos etc.).
  - **Expense**: saídas de dinheiro para fora (contas, mercado, lazer etc.).
  - **Transfer**: movimentação entre contas da mesma pessoa/família (ex.: ABN → Revolut, conta corrente → poupança).
  - **Contribution**: saídas da conta corrente para contas de investimento (aportes em corretora, savings com objetivo de investimento).
  - **Withdrawal**: saídas de contas de investimento de volta para conta corrente (resgates, saques).
  - **Adjustment**: ajustes manuais/exceções (correções pontuais).
- `categoria` (ex.: HOME, TRANSPORT, LEISURE)  
- `subcategoria` (ex.: Mortgage, Market, Restaurant)  
- `valor_original`  
- `moeda_original` (EUR, BRL, USD, cripto)  
- `valor_moeda_base`  
- `moeda_base`  
- `ativo` (quando aplicável)  
- `classe_ativo` (Ação, ETF, FII, Renda Fixa, Previdência, Cripto etc.)  

O sistema deve manter tabelas auxiliares para:

- **Categorias:** tipo (Receita/Despesa), categoria, subcategoria, grupo macro (ex.: Fixa/Variável).  
- **Ativos:** ticker, nome, classe de ativo e outros campos relevantes.  

### F3 – Moedas e moeda base

- O sistema deve permitir que o usuário escolha uma **moeda base** (ex.: EUR) para consolidação dos dados.  
- O sistema deve converter `valor_original` para `valor_moeda_base` usando taxas de câmbio configuráveis (tabela de câmbio ou API em versões futuras).  
- O sistema deve suportar pelo menos EUR, BRL, USD e principais criptomoedas (convertidas para a moeda base por uma taxa de referência).  

### F4 – Categorização automática com regras

- O sistema deve manter um **dicionário de categorização** baseado em:  
  - palavras‑chave na descrição,  
  - instituição,  
  - tipo de transação,  
  - combinações simples desses atributos.  
- Ao importar novas transações, o sistema deve aplicar o dicionário para definir `categoria` e `subcategoria` automaticamente.  
- Se uma transação não se encaixar em nenhuma regra, deve ser marcada como “Não categorizada”.  
- A interface deve permitir que o usuário:  
  - Revise transações não categorizadas.  
  - Escolha tipo, categoria e subcategoria.  
  - Opcionalmente crie uma nova regra para que transações semelhantes futuras sejam categorizadas automaticamente.  

### F5 – Orçamento e regras de investimento

- O sistema deve permitir configurar, via interface:  
  - Percentual da receita mensal destinado a investimentos.  
  - Divisão dos investimentos entre objetivos/caixinhas (percentuais e valores fixos).  
- Para o período selecionado, o sistema deve:  
  - Calcular a receita consolidada.  
  - Calcular o valor total a investir.  
  - Calcular o aporte recomendado para cada objetivo.  

### F6 – Monitor de alocação e rebalanceamento

- O sistema deve permitir definir alocação alvo por classe de ativo (em porcentagem).  
- O sistema deve calcular a alocação atual com base no valor em moeda base de cada classe.  
- Para cada classe, o sistema deve exibir:  
  - Alvo (%), Atual (%) e diferença em pontos percentuais.  
- O sistema deve destacar classes cuja diferença absoluta seja maior ou igual a 5 p.p.  
- O sistema deve sugerir, para classes desviadas, quanto comprar ou vender para voltar à alocação alvo, considerando o valor total atual da carteira.  

### F7 – Tratamento especial de Tikkie

- O sistema deve identificar transações ligadas ao Tikkie nos extratos do ABN, preferencialmente por padrões na descrição.  
- Deve suportar dois cenários principais:  
  - **Reembolso de despesa compartilhada:** gasto inicial (ex.: restaurante) seguido de recebimentos via Tikkie; o gasto líquido é o valor do restaurante menos os reembolsos, lançado na categoria original (ex.: LAZER / Restaurante).  
  - **Coleta para presentes/outros:** pagamentos Tikkie usados para juntar dinheiro para presentes; o valor líquido deve ser classificado em categoria apropriada (ex.: OUTROS / Presentes).  
- No MVP, o matching pode usar regras simples (data e valores aproximados) e permitir correção manual posterior.  

### F8 – Autenticação e multiusuário básico

- O sistema deve exigir login (usuário/senha) antes de exibir dados.  
- Deve usar um módulo de autenticação seguro para Streamlit, armazenando senhas com hash e mantendo a configuração de usuários reais fora do repositório público.  
- Deve suportar pelo menos dois usuários na “instância familiar” (autor e esposa) e ser projetado para, no futuro, comportar múltiplas contas independentes.  

## 4. Requisitos não funcionais

- **Custo:** usar serviços gratuitos ou de baixo custo (Python, Streamlit, Streamlit Community Cloud, GitHub).  
- **Desempenho:** o processamento mensal dos arquivos deve terminar em segundos/minutos, considerando o tamanho típico dos extratos.  
- **Segurança / privacidade:**  
  - Dados reais nunca devem ser versionados no repositório público.  
  - Arquivos sensíveis e configurações devem ser listados no `.gitignore` (ex.: `data/real/`, `config/config.yaml`, `.streamlit/secrets.toml`, `.env`).  
- **Manutenibilidade:**  
  - Código organizado em módulos (`src/data`, `src/domain`, `src/utils`, `app/`).  
  - Uso de `requirements.txt` para reprodutibilidade do ambiente.  

## 5. Estrutura de pastas do projeto

personal_finance_app/
├── app/
│   └── app.py               # App Streamlit
├── src/
│   ├── data/
│   │   ├── loaders.py       # Leitura de arquivos das instituições
│   │   └── transformers.py  # Padronização e unificação das transações
│   ├── domain/
│   │   ├── budgeting.py     # Regras de orçamento/aportes
│   │   └── allocation.py    # Alocação de carteira e rebalanceamento
│   └── utils/
│       └── categorization.py # Motor de categorização (dicionário de regras)
├── config/
│   ├── config_example.yaml  # Exemplo de config (sem dados sensíveis)
├── data/
│   ├── example/             # Dados fictícios para demonstração
│   └── real/                # Dados reais (gitignored)
├── docs/
│   └── projeto_financas.md  # Este documento
├── tests/
├── requirements.txt
├── .gitignore
└── README.md