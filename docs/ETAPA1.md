# OXICOR — Hora da Prática 1

Projeto acadêmico da PUCPR voltado à educação em saúde cardiometabólica.

O propósito da OXICOR é **“Levar saúde ao longo do caminho”**, aproximando prevenção, informação e tecnologia do dia a dia das pessoas.

## 1. CBL — Aprendizagem Baseada em Desafios

### Grande Ideia

Tecnologia e inteligência artificial aplicadas à prevenção e à educação em saúde cardiometabólica.

### Pergunta Essencial

Como a inteligência artificial pode transformar dados de saúde e conhecimento científico em informações acessíveis que ajudem as pessoas a compreender melhor seus riscos cardiometabólicos?

### Desafio

Desenvolver um assistente educacional inteligente para a OXICOR que integre dados estruturados de triagem cardiometabólica com uma base científica sobre hipertensão, obesidade e diabetes tipo 2, permitindo consultas em linguagem natural e respostas fundamentadas por RAG.

### Justificativa Pessoal

Atuo na área da saúde e, há mais de uma década, na área cardiovascular. Ao longo do tempo, com os conhecimentos adquiridos na pós-graduação em Saúde 4.0, percebi que existe uma mudança de pensamentos sobre a manutenção da qualidade de vida. Um dos focos difundidos atualmente é a prevenção, com atenção a fatores de risco modificáveis e à identificação precoce de alterações cardiometabólicas.

Gostaria de unir a experiência que tenho na área da saúde e inteligência artificial para trazer melhor acesso a informações e conhecimento sobre prevenções e fatores de risco no dia a dia.

Gostaria, nessa fase do projeto, de tentar alinhar uma base clínica fundamentada em conhecimento científico com automação, utilizando dados de triagem e pipelines para organizar e apoiar a entrega de conhecimento sem substituir o profissional de saúde.

## 2. Objetivo e escopo

Esta etapa desenvolve um assistente educacional que integra conhecimento científico, dados estruturados e automação para apoiar a educação sobre risco cardiometabólico, sem substituir profissionais de saúde.

A aplicação oferece duas áreas:

- **Chat:** perguntas educativas respondidas pelo AgentFlow com apoio da base científica.
- **Relatórios:** consultas de leitura ao PostgreSQL, indicadores, tabelas, gráfico de risco e duas intenções controladas em linguagem natural.

A integração ocorre na interface. O chat não executa SQL livre e os relatórios não usam IA para gerar consultas. Esta pasta contém o Streamlit; Flowise, Ollama, Knowledge Base e PostgreSQL são serviços externos previamente configurados. Não há provisionamento completo desses serviços nesta pasta.

## 3. Arquitetura real

```text
Streamlit
├── Chat → Flowise AgentFlow → Ollama
│            └── Knowledge Base / RAG
│                 └── Retriever Tool → Faiss + embeddings
│                     └── trechos recuperados → contexto da resposta
├── Relatórios → PostgreSQL → pandas → indicadores e tabelas
└── Histórico visual → SQLite persistente
```

O Flowise coordena o modelo e a recuperação da Knowledge. O Ollama não consulta o índice autonomamente: o Retriever Tool fornece trechos para o contexto do Agent.

Fluxo RAG: **Streamlit → Flowise AgentFlow → Knowledge Base / Retriever → Ollama**. Fluxo de dados estruturados: **Streamlit → PostgreSQL → participantes + triagens**. O Flowise é o orquestrador equivalente do pipeline RAG; o índice Faiss é o armazenamento vetorial equivalente, sem uso de txtai ou ChromaDB nesta implementação.

Nos relatórios, o Psycopg executa consultas fixas ou parametrizadas. Os resultados são convertidos em DataFrames pandas e apresentados no Streamlit. Não há gravação de triagens nem recálculo de classificações clínicas nesta aplicação.

## 4. Tecnologias utilizadas

| Tecnologia | Papel |
|---|---|
| Python 3.12 | Runtime definido no Dockerfile |
| Streamlit | Interface, callbacks, estado e streaming |
| Requests | Comunicação HTTP/SSE com Flowise |
| Flowise | Orquestração do Agent e da Knowledge |
| Ollama | Inferência local e embeddings |
| PostgreSQL | Dados estruturados de participantes e triagens |
| pandas | Organização dos resultados em DataFrames |
| Psycopg 3 | Conexão e SQL parametrizado |
| Docker Compose | Serviço `chat` e volume persistente |
| SQLite | Histórico visual das conversas |
| RAG, Faiss e `nomic-embed-text` | Recuperação semântica de trechos científicos |

Na inspeção de 16/09/2026, o AgentFlow `OXICOR_AGENT_PUCPR_V1` estava configurado com **`qwen3:4b-instruct-oxicor-cpu`**. Esse modelo é um recurso externo do Ollama, não distribuído nesta pasta. Subir o Compose do Streamlit não cria o modelo nem o AgentFlow.

## 5. Dados estruturados e relatórios

O banco existente é `oxicor`. O **PostgreSQL é utilizado como equivalente ao DuckDB** para a finalidade acadêmica de consultar dados estruturados, aproveitando a infraestrutura existente. Não foi adicionado DuckDB nem migrado o banco; o enquadramento final na rubrica cabe à avaliação acadêmica.

As tabelas `participantes` e `triagens` são relacionadas logicamente por `paciente_id`. Um participante pode ter várias triagens. O código pressupõe essas tabelas já existentes; esta pasta não inclui scripts de criação ou carga.

### Dados estruturados de demonstração

Os arquivos `data/participantes.csv` (7 registros) e `data/triagens.csv` (9 registros) foram recuperados sem alteração de valores do pacote anterior `Documento_Oxicor_flowai.zip`. Ambos contêm `paciente_id`, e todas as triagens referenciam participantes presentes no primeiro arquivo. O autor confirmou que os registros são fictícios, inclusive o identificador sem marca explícita de teste.

Esses CSVs acompanham a entrega como duas tabelas relacionadas. A aplicação funcional continua consultando PostgreSQL, equivalente ao DuckDB; não carrega esses CSVs automaticamente nem modifica o banco. A regra `data/` do `.gitignore` existente permanece inalterada: os dois CSVs estão incluídos explicitamente no ZIP, mas não são adicionados automaticamente ao Git.

Campos utilizados em `triagens`: `triagem_id`, `paciente_id`, `data_coleta`, `pas`, `pad`, `risco`, `alerta_critico` e `status_sindrome_metabolica`. A tabela `participantes` fornece a contagem e os IDs disponíveis.

| Relatório | Comportamento |
|---|---|
| Total de participantes | Contagem de registros em `participantes` |
| Participantes com PA acima | Participantes distintos com alguma triagem em que `pas >= 130 OR pad >= 85` |
| Distribuição por risco | Contagem de triagens por risco já registrado |
| Última pressão por participante | ID parametrizado; ordem `data_coleta DESC, triagem_id DESC LIMIT 1` |
| Triagens com alerta crítico | Booleano verdadeiro ou inteiro 1, após conferir tipo e valores |
| Síndrome metabólica | Distribuição pelos status registrados, com filtro opcional, sem inferir diagnóstico |

A interface também mostra total de triagens e o SQL utilizado. Risco, alertas e síndrome metabólica contam **triagens**, não necessariamente pessoas únicas. Datas nulas seguem a semântica de ordenação do PostgreSQL da query existente.

**Distinção importante:** 130/85 mmHg é o critério operacional do relatório “PA acima”, não diagnóstico de hipertensão. Não deve ser confundido com 140/90 mmHg, critério descrito no documento de hipertensão do RAG.

### Consultas em linguagem natural

Em **Relatórios → Pergunte aos dados**, `natural_reports.py` reconhece duas intenções por regras textuais, tolerando caixa e acentos. Não utiliza LLM nem executa SQL arbitrário.

- `Quantos participantes tiveram pressão acima da faixa esperada?`
- `Qual foi a última pressão registrada do participante ID?`

Substitua `ID` por um identificador existente, preservando a grafia. Perguntas fora dos padrões implementados recebem aviso de não reconhecimento. O identificador é passado separadamente como parâmetro SQL.

## 6. RAG e base científica

A inspeção em leitura confirmou a Knowledge **`OXICOR_RAG_PUCPR_V1`**, status `UPSERTED`, três documentos processados e **16 chunks**:

| Conteúdo conferido nos chunks | Chunks |
|---|---:|
| Hipertensão arterial e pressão arterial — resumo educacional | 5 |
| Obesidade e prevenção de doença cardiovascular — resumo educacional | 5 |
| Diabetes mellitus tipo 2 e glicemia — resumo educacional | 6 |
| **Total** | **16** |

São resumos científicos dos três temas. O loader do terceiro documento repete o nome exibido do resumo de obesidade, mas **seus chunks contêm o resumo de DM2**, conforme conferência do conteúdo. Essa divergência de rótulo não foi alterada.

Configuração inspecionada:

- Vector store: **Faiss**.
- Base Path: `faiss/oxicor_rag_pucpr_v1`.
- Top K: **4**.
- Embeddings: **`nomic-embed-text`**, via Ollama.
- Base URL interna: `http://host.docker.internal:11434`.

O Retriever Tool associado à Knowledge realiza busca semântica no índice. Os trechos recuperados compõem o contexto entregue ao Agent para gerar a resposta. O índice e o AgentFlow ficam no ambiente Flowise externo e não são criados pelo Compose desta aplicação.

As cópias integrais dos três resumos originais utilizados na Knowledge acompanham a entrega:

- `rag/OXICOR_RAG_01_HIPERTENSAO_RESUMO.md`
- `rag/OXICOR_RAG_02_OBESIDADE_CARDIOVASCULAR_RESUMO.md`
- `rag/OXICOR_RAG_03_DM2_RESUMO.md`

A procedência foi conferida comparando o conteúdo dos originais com os 16 chunks da Knowledge (5 + 5 + 6). Os arquivos foram copiados sem reescrita ou nova sumarização; nenhum índice, documento ou configuração do Flowise foi alterado.

### System Prompt

O arquivo `config/system_prompt.txt` contém uma cópia textual exata do System Prompt real recuperado em leitura do AgentFlow `OXICOR_AGENT_PUCPR_V1`. É um registro documental, não uma nova configuração ou um novo prompt. Ele contextualiza o assistente para educação em saúde cardiometabólica e prioriza o conteúdo recuperado.

O prompt do Agent exige consulta à Knowledge nos temas cobertos, prioridade à base científica, preservação dos valores e condições recuperados, ausência de invenções e declaração explícita quando não houver informação suficiente. Orienta resposta em português do Brasil, proíbe diagnóstico e prescrição e solicita não expor raciocínio interno.

Essas instruções não garantem, por si só, correção clínica: a resposta deve ser conferida com os trechos recuperados.

### Perguntas de demonstração do RAG

1. Segundo a base científica OXICOR, quais valores definem hipertensão arterial?
2. Por que a obesidade aumenta o risco cardiovascular?
3. Qual a relação entre diabetes tipo 2 e risco cardiovascular?

Para a primeira pergunta, o documento indexado descreve PAS ≥ 140 mmHg e/ou PAD ≥ 90 mmHg em duas ocasiões diferentes. Esse é um ponto de conferência documental, não orientação para autodiagnóstico. Nas demais perguntas, conferir se a resposta se limita às informações recuperadas e reconhece lacunas.

## 7. Interface e histórico

- `st.session_state` mantém estado temporário entre reruns.
- Callbacks criam novas conversas e selecionam as anteriores.
- Cada conversa recebe um identificador enviado ao Flowise em `chatId` e `overrideConfig.sessionId`. A memória do Agent depende do fluxo externo.
- SSE é recebido por Requests e exibido progressivamente por `st.write_stream`. Retorno JSON integral é identificado como tal.
- Um filtro de apresentação oculta thinking e blocos internos identificáveis sem reescrever a resposta final. Conteúdo interno sem marcadores reconhecíveis não pode ser distinguido com garantia de texto comum.
- O histórico persistente fica em `/app/data/history.sqlite3`, no volume `streamlit-flowise-chat_chat_history`, incluindo títulos, mensagens, identificadores, timestamps e conversa ativa.

O volume preserva o histórico após recriação do container. O histórico é **compartilhado entre as abas e navegadores da instância**, sem contas ou isolamento por usuário. Uma interrupção durante a geração pode perder tokens ainda não salvos e deixar resposta incompleta identificada. Não há reenvio automático.

## 8. Estrutura do projeto

Árvore desta pasta, baseada nos arquivos existentes:

```text
streamlit-flowise/
├── data/
│   ├── participantes.csv
│   └── triagens.csv
├── rag/
│   ├── OXICOR_RAG_01_HIPERTENSAO_RESUMO.md
│   ├── OXICOR_RAG_02_OBESIDADE_CARDIOVASCULAR_RESUMO.md
│   └── OXICOR_RAG_03_DM2_RESUMO.md
├── config/
│   └── system_prompt.txt
├── docs/                        # dois guias; links na seção 12
├── .dockerignore
├── .env.example                 # modelo sem credenciais
├── .gitignore
├── app.py
├── compose.yaml
├── Dockerfile
├── natural_reports.py
├── README.md
├── reporting.py
├── reports_ui.py
├── requirements.txt
└── start.ps1
```

O `.bak` é um backup local, não o código executado. O banco SQLite fica no volume Docker, fora dessa árvore. Revisar backups e históricos antes de qualquer compartilhamento. **Excluir obrigatoriamente do ZIP final `.env` e `app.py.before-thinking-filter-20260913.bak`, sem apagar os arquivos locais.** O `.gitignore` não aplica essas exclusões automaticamente a um ZIP criado manualmente.

## 9. Configuração e execução

### Pré-requisitos

- Docker Desktop aberto, com containers Linux e Docker Compose.
- Flowise disponível na porta 3000, com AgentFlow e Knowledge configurados.
- Ollama acessível pelo Flowise, com modelo de chat e embeddings disponíveis.
- PostgreSQL na porta 5432, banco `oxicor`, tabelas existentes e usuário autorizado para leitura.

Este Compose define **somente o serviço `chat`**. Não provisiona banco, Flowise, Ollama ou índice. Uma reprodução completa exige também esses recursos externos; esta pasta não contém export do AgentFlow, definição do modelo personalizado nem scripts de schema.

### Configurar o ambiente local

Abra o PowerShell na pasta que contém `compose.yaml`. Copie o exemplo apenas se não existir configuração local:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Preencha localmente. Os exemplos abaixo são apenas placeholders, nunca credenciais reais:

```dotenv
FLOWISE_API_KEY=SUA_CHAVE_AQUI
POSTGRES_PASSWORD=SUA_SENHA_AQUI
```

Variáveis de configuração:

| Variável | Finalidade |
|---|---|
| `FLOWISE_API_URL` | Endpoint `/api/v1/prediction/SEU_FLOW_ID` |
| `FLOWISE_API_KEY` | Chave do fluxo, se exigida, sem prefixo `Bearer` |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Endereço e porta |
| `POSTGRES_DB` | Banco existente |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciais autorizadas |
| `CHAT_HISTORY_DB` | Padrão: `/app/data/history.sqlite3` |

Dentro do container, `localhost` aponta para o próprio container. O exemplo usa `host.docker.internal` para os serviços publicados no Windows. **Não enviar o .env real na entrega.**

### Como iniciar manualmente

Com Docker no PATH, dentro desta pasta:

```powershell
docker compose up -d --build --no-deps chat
docker compose ps
```

Alternativa existente para Windows, inclusive quando Docker não está no PATH:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

O script localiza o Docker e usa `compose up -d --build --force-recreate`. Nesta pasta há somente o serviço `chat`.

Abra [Streamlit](http://localhost:8501). O [Flowise](http://localhost:3000) deve estar rodando separadamente. A porta 8501 é publicada somente em `127.0.0.1`.

O `requirements.txt` declara Streamlit, Requests, pandas e Psycopg. As dependências são instaladas na imagem Docker; não é necessário instalar Streamlit no Python do Windows. São usadas faixas de versões, não um arquivo de lock.

### Parar e reaplicar configuração

```powershell
# Parar somente a interface, preservando o volume:
docker compose stop chat

# Reaplicar alterações locais de código ou ambiente:
docker compose up -d --build --no-deps chat
```

**Não executar `docker compose down -v`** para preservar o histórico: a opção remove volumes. Alterações somente no Streamlit não exigem reiniciar Flowise, Ollama ou PostgreSQL.

## 10. Roteiro de demonstração acadêmica

1. Abrir o Chat, iniciar **Nova conversa** e enviar uma pergunta científica.
2. Conferir a fundamentação nos trechos recuperados no Flowise e a conclusão do streaming.
3. Criar outra conversa e retomar a anterior pela barra lateral.
4. Abrir **Relatórios**, conferir a indicação de conexão (`SELECT 1`) e os seis relatórios.
5. Executar as duas perguntas controladas de dados usando um ID existente; abrir **Ver SQL**.
6. Distinguir ausência de registros de falha de conexão, sem criar dados fictícios automaticamente.

Este README foi elaborado por inspeção de arquivos e configuração. Não equivale a uma nova execução de todos os testes de integração; disponibilidade e credenciais devem ser verificadas antes da demonstração.

## 11. Segurança e limitações

O `.gitignore` exclui arquivos de ambiente reais, SQLite, logs e diretórios temporários, preservando `.env.example`. O `.dockerignore` exclui os arquivos de ambiente do contexto de build. Secrets são lidos no servidor, não devem aparecer no código ou na entrega. Arquivos ignorados que já tenham sido rastreados exigem revisão antes de compartilhamento.

Os relatórios usam transações somente leitura e parâmetros SQL. Não alteram registros, schemas ou classificações. O SQLite do chat é separado do PostgreSQL das triagens.

A inferência observada é local, em CPU. Hardware, contexto e histórico da sessão influenciam a latência, que pode chegar a vários minutos. Streaming e ocultação de thinking não eliminam esse custo. Não há promessa de tempo fixo ou precisão clínica absoluta.

A base é limitada aos documentos indexados. O protótipo não possui autenticação de usuários finais nem isolamento de histórico e não deve ser apresentado como sistema clínico de produção. Usar somente dados autorizados, evitando dados pessoais no chat, capturas e apresentação.

## 12. Documentação complementar

- [PostgreSQL, pandas e relatórios](docs/%70ostgresql_relatorios.md).
- [Streaming, session_state, callbacks e persistência](docs/streamlit_conceitos.md).

Esses documentos contêm testes históricos com datas e limitações daquele momento; não comprovam automaticamente o estado atual de todos os serviços.

**Esta orientação tem finalidade educativa e não substitui avaliação por profissional de saúde.**
