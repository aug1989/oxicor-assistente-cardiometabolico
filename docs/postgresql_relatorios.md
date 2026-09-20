# PostgreSQL, pandas e relatórios OXICOR

Arquitetura: **PostgreSQL → SQL parametrizado → pandas DataFrame → Streamlit**.

O banco `oxicor` existente é a fonte dos relatórios. PostgreSQL é utilizado como equivalente ao DuckDB para a consulta e análise de dados estruturados, aproveitando as tabelas já integradas ao projeto. Conforme o enunciado informado pelo projeto, a rubrica prevê “DuckDB ou equivalente”; a interpretação final cabe à avaliação acadêmica. Não foi adicionado DuckDB nem migrado o banco.

## Aplicação e configuração

A aplicação fica em `<PASTA_DO_PROJETO>\streamlit-flowise`, separada da infraestrutura inicial em `oxicor-etapa1`.

As variáveis `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` são carregadas pelo `env_file` já existente no Compose. Para PostgreSQL no Windows, o container usa `host.docker.internal`, porta `5432`, banco `oxicor`. A senha deve ser preenchida somente no `.env` local, que permanece ignorado pelo Git e excluído da imagem. Valores Flowise existentes são preservados. Não há senha no código, SQL visível ou mensagens de erro.

Após configurar a senha, no diretório da aplicação:

```powershell
docker compose up -d --build --no-deps chat
```

Somente o serviço Streamlit é reconstruído/recriado. A definição do Compose e o volume `streamlit-flowise-chat_chat_history`, montado em `/app/data`, são preservados. Não usar `down -v`.

## Acesso e métricas

Em `http://localhost:8501`, a navegação lateral alterna entre **Chat** e **Relatórios**. O módulo `reporting.py` mantém as consultas fora do código visual. `reports_ui.py` apresenta os DataFrames, SQL e KPIs. O chat mantém callbacks, session_state, gerador SSE e histórico SQLite existentes.

Tabelas usadas: `participantes` e `triagens`. Não há DDL, INSERT, UPDATE ou DELETE nos relatórios. As transações usam `READ ONLY`, snapshot consistente e limite de 10 segundos por instrução. As consultas não ficam em cache e são refeitas ao abrir/atualizar a área.

1. **Total de participantes:** linhas em `participantes`.
2. **PA acima:** participantes distintos com alguma triagem em que `pas >= 130 OR pad >= 85`. Não considera apenas a última triagem.
3. **Risco:** quantidade de triagens por valor já gravado em `risco`.
4. **Última pressão:** participante escolhido entre os IDs existentes, parâmetro SQL, ordem `data_coleta DESC, triagem_id DESC LIMIT 1`. A ordem solicitada foi preservada, inclusive a semântica PostgreSQL para datas nulas.
5. **Alerta crítico:** o tipo real da coluna é inspecionado antes do filtro. Boolean usa `IS TRUE`; inteiro estritamente 0/1 usa `= 1`. Outros formatos pedem conferência e não são interpretados automaticamente.
6. **Síndrome metabólica:** distribuição pelos valores reais de `status_sindrome_metabolica`, com filtro opcional para selecionar o status provável/positivo observado. Não se presume equivalência entre rótulos nem se recalcula diagnóstico. A consulta definitiva de um subconjunto clínico depende de conferir os valores reais do banco.

KPIs: total de participantes, participantes com PA acima, triagens com alerta crítico e total de triagens. Risco tem gráfico de barras; os demais relatórios têm tabelas. Datas usam dia/mês/ano e hora; PAS/PAD indicam mmHg; alertas booleanos são mostrados como Sim/Não. O SQL de cada relatório aparece em **Ver SQL**, sem credenciais. Ausência de registros tem mensagem explícita e não gera dados fictícios.

## Dependências e validação

`pandas>=2.2,<3` (antes transitivo do Streamlit) e `psycopg[binary]>=3.2,<4` estão declarados explicitamente. O cursor Psycopg executa SQL parametrizado e o resultado é convertido em DataFrame sem SQLAlchemy adicional. Referências: [pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) e [Psycopg](https://www.psycopg.org/psycopg3/docs/).

Sem `POSTGRES_PASSWORD`, Relatórios exibe configuração pendente e Chat permanece disponível. É necessário testar `SELECT 1`, inspecionar contagens/categorias reais e testar os seis relatórios com a credencial configurada. Nunca copiar credenciais ou mensagens clínicas para logs de diagnóstico. Não inserir dados fictícios sem autorização.

## Registro histórico de validação — 09/09/2026

Os resultados abaixo descrevem exclusivamente o teste daquela data. Não indicam a disponibilidade, configuração ou estado atual dos serviços; uma demonstração exige nova validação no ambiente de execução.

- Somente o container Streamlit foi reconstruído e recriado; o Compose e o volume existente foram mantidos.
- Sintaxe dos três módulos Python validada. Chat e Relatórios abriram sem exceções no teste de interface e no navegador.
- Antes e depois da recriação, as 10 conversas existentes tiveram conteúdo idêntico, verificado por hash. O teste solicitado criou uma nova conversa com “oi”, recebeu resposta por SSE e preservou as anteriores.
- O container alcançou `host.docker.internal:5432` via TCP.
- Naquele teste, a autenticação PostgreSQL e `SELECT 1` não foram validados porque a variável de senha não estava preenchida. Contagens, categorias e consulta por participante ficaram fora daquela validação. Isso não descreve a configuração atual. Acesso TCP, isoladamente, não comprova autenticação no banco.
- Nenhuma alteração de Flowise, AgentFlow, RAG, Ollama, n8n ou schema/dados PostgreSQL foi realizada.
