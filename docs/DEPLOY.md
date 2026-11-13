# Publicação do OXICOR no Streamlit Community Cloud

Estado em 13/11/2026: demonstração publicada em **https://oxicor-aug1989.streamlit.app/**, a partir da branch `etapa3-deploy`, com `app.py` e Python 3.12. O provedor de IA configurado é OpenRouter, modelo `google/gemini-2.5-flash-lite`. Não há credenciais neste documento.

O autor apresentou no site respostas de RAG, consulta DuckDB de sete participantes, classificação ML de perfil fictício e relatórios com sete participantes e nove triagens. São verificações de cenários de demonstração; não equivalem à validação clínica, à execução completa do golden dataset no novo provedor ou a testes de carga/isolamento real entre sessões.

## Arquivos e dependências

- `app.py` é o ponto de entrada Streamlit.
- `requirements.txt` contém dependências de execução com versões diretas fixadas. `requirements-test.txt` inclui essas dependências e acrescenta `pytest` e `deepeval`, sem instalar a suíte de avaliação pesada no app de produção.
- `packages.txt` instala `libgomp1`, necessário para operações do scikit-learn em Linux.
- O Community Cloud instala `requirements.txt` e `packages.txt`; ele não executa o `Dockerfile` nem o `compose.yaml` do projeto. Consulte a [documentação de dependências do Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

As versões diretas foram fixadas a partir do ambiente da imagem `oxicor-clone-chat:latest` disponível durante esta preparação. A resolução transitiva ainda pode variar; uma publicação deve validar o build real na plataforma.

## Criar o app

1. Envie a branch `etapa3-deploy` ao GitHub após revisar as alterações.
2. No Streamlit Community Cloud, crie o app apontando para esse repositório, branch `etapa3-deploy` e arquivo `app.py`.
3. Use Python 3.12, compatível com a imagem de execução e os artefatos existentes.
4. Configure apenas os secrets necessários na área **App settings → Secrets**. Nunca publique `.env` ou `secrets.toml`.
5. Inicie o app e valide as limitações e os fluxos descritos abaixo antes de divulgar a URL.

A configuração local por variáveis de ambiente e a configuração Cloud por `st.secrets` usam os mesmos nomes. Uma variável de ambiente não vazia tem precedência; quando ausente ou vazia, o app consulta os secrets do Streamlit. Não coloque valores de credenciais neste documento.

## Configurações

| Nome | Obrigatório? | Finalidade e comportamento |
|---|---|---|
| `CREWAI_BASE_URL` | Sim para o chat | Endereço de API acessível pelo app hospedado. `host.docker.internal` aponta para a configuração Docker local e não deve ser usado para alcançar o notebook na nuvem. |
| `CREWAI_LLM` | Sim para o chat | Identificador/modelo aceito pelo adaptador CrewAI escolhido. |
| `CREWAI_API_KEY` | Conforme o provedor | Credencial da API, se exigida. Ollama local usa o valor convencional configurado no `.env.example`; isso não torna o notebook acessível pela nuvem. |
| `OXICOR_RAG_BACKEND` | Não | Padrão `local`, que consulta os Markdown do repositório. `flowise` exige configurar `FLOWISE_API_URL` e, se necessário, `FLOWISE_API_KEY`; é integração opcional. |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Não | Se todos forem configurados, habilitam Relatórios via PostgreSQL; use somente base fictícia e permissões de leitura. Se nenhum for configurado, Relatórios usa o DuckDB local de demonstração. Configuração parcial é reportada como erro, sem fallback silencioso. |
| `OXICOR_DATA_DIR` | Não | Diretório gravável dos arquivos transitórios. O padrão é `/tmp/oxicor` na hospedagem; no Docker local permanece `/app/data`. O armazenamento Community Cloud é efêmero. |
| `OXICOR_DUCKDB_PATH` | Não | Substitui o caminho do banco DuckDB reconstruído dos CSVs de demonstração. |
| `OXICOR_ADMIN_PAGES_ENABLED` | Não; padrão `false` | Expõe as páginas Observabilidade e Avaliação. Não habilite numa publicação pública sem autenticação e revisão de acesso. |
| `OXICOR_OBSERVABILITY_ENABLED` | Não; padrão `false` | Habilita persistência local transitória de traces. Desativado, os traces não são gravados nem exportados pelo fluxo de atendimento. |
| `OXICOR_LANGFUSE_ENABLED` | Não; padrão `false` | Integração externa opcional. Exige habilitação explícita, chaves e URL; não configure enquanto o destino e o tratamento de dados não forem aprovados. |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | Não | Secrets da integração Langfuse opt-in. |
| `FLOWISE_API_URL`, `FLOWISE_API_KEY` | Não | Configuração opcional do backend RAG Flowise. |

Para reproduzir a publicação, configure seu próprio modelo e chave no Community Cloud. A interface avisa que o chat depende do par `OPENROUTER_MODEL`/`OPENROUTER_API_KEY` ou da configuração alternativa `CREWAI_*`; ao enviar uma pergunta sem essas definições, apresenta indisponibilidade, sem chamar um modelo ou fabricar resposta.

## Dados, histórico e arquivos graváveis

- Conversas e IDs de sessão Flowise permanecem somente em `st.session_state`, isolados por sessão Streamlit. O app não carrega nem grava o histórico compartilhado SQLite anterior. Uma nova sessão ou reinicialização pode perder o histórico; não há garantia de persistência.
- Os bancos, resultados de execução e arquivos de treinamento graváveis usam `OXICOR_DATA_DIR` ou caminhos substituíveis por configuração. Os arquivos temporários do Community Cloud não são armazenamento durável e podem ser removidos em reinicialização ou suspensão.
- O DuckDB é inicializado sob demanda a partir dos CSVs disponíveis no repositório. O app também usa o corpus Markdown local, o modelo preditivo já versionado e o dataset CDC público.
- Sem configuração PostgreSQL, Relatórios usa `participantes.csv` e `triagens.csv` para demonstrar totais de participantes/triagens, participantes distintos com PAS ≥ 130 ou PAD ≥ 85 (critério operacional existente, não diagnóstico), contagens das categorias gravadas de risco e síndrome metabólica, valores booleanos já gravados de alerta crítico e a última pressão disponível para um ID existente. Essas operações são consultas somente leitura sobre tabelas locais; não são criados participantes/triagens nem recalculadas classificações. O indicador de PA acima é um filtro operacional do projeto, não conclusão clínica.
- A interface identifica essa fonte como **Dados fictícios de demonstração**. As colunas disponíveis são: `participantes(paciente_id, idade, sexo)` e `triagens(triagem_id, paciente_id, data_coleta, pas, pad, glicemia, tipo_glicemia, imc, cintura, triglicerideos, hdl, score, risco, classificacao_pressorica, status_sindrome_metabolica, alerta_critico)`. Só os campos necessários às tabelas/indicadores acima são apresentados. A integração PostgreSQL continua opcional e é usada quando todos os secrets requeridos existem.
- Antes da publicação, confirme que os CSVs versionados continuam sendo os dados fictícios destinados à demonstração. Nunca conecte dados reais de saúde a uma instância pública sem decisão e controles apropriados.
- Não configure dados reais de saúde ou identificação. O mascaramento existente é best-effort e não garante anonimização.
- O arquivo SQLite de histórico e os volumes/container antigos não foram apagados, migrados ou transformados por esta preparação. O código novo simplesmente não carrega esse histórico para as sessões do app.

## Páginas e segurança

Chat, Relatórios e ML Tradicional continuam no menu. Relatórios funciona com a fonte local fictícia sem PostgreSQL e mantém PostgreSQL opcional. Treinamento de ML e o carregamento de bibliotecas podem exceder os recursos gratuitos, então precisam de validação prática.

Observabilidade e Avaliação continuam implementadas, mas ficam fora do menu por padrão. A página de traces não deve ser exposta a visitantes sem autenticação: traces podem conter perguntas e respostas, mesmo após mascaramento. Para testar localmente em ambiente controlado, habilite as flags correspondentes; não habilite as páginas administrativas em uma instância pública aberta. Langfuse também permanece desativado por padrão.

O histórico por sessão reduz a exposição entre sessões do app, mas não é autenticação nem mecanismo para armazenar dados clínicos. Exiba orientação para usar somente exemplos fictícios.

## Limitações confirmadas e validações pendentes

**Observado na demonstração publicada:** inicialização da interface, recuperação dos resumos, utilização do modelo salvo e consultas aos CSVs fictícios. O build conseguiu instalar as dependências necessárias a esses exemplos.

**Ainda não validado:** carga concorrente, isolamento entre duas sessões reais, treinamento completo na nuvem, conexão real com PostgreSQL e execução completa dos quinze casos DeepEval com o provedor publicado. Não foram caracterizados custo médio, latência e disponibilidade sob uso contínuo. Consulte os limites vigentes da hospedagem ao planejar uso além da demonstração acadêmica.

## Verificações antes de divulgar

Instale dependências de teste em ambiente virtual separado, sem usar o ambiente de produção:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-test.txt
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:DEEPEVAL_DISABLE_DOTENV = "1"
$env:DEEPEVAL_TELEMETRY_OPT_OUT = "YES"
.\.venv\Scripts\python -m pytest -ra -p no:cacheprovider tests
```

Essas flags evitam autoload do plugin DeepEval e desabilitam dotenv/telemetria nessa suíte unitária. Ela não executa inferência nem prova o deploy. Preserve `evaluation/golden.json`, os critérios DeepEval e as evidências anteriores. A suíte DeepEval de `evaluation/test_deepeval.py` é separada e realiza inferência real; só a execute após configurar e aprovar um provedor. A validação de ponta a ponta exige o app implantado, o provedor de IA escolhido e testes explícitos de duas sessões no navegador. Não divulgue uma URL até confirmar que o app está acessível e esses fluxos foram exercitados.

## Estado da entrega

- Publicação acadêmica disponível com chat, Relatórios e ML; uso apenas educacional e com dados fictícios.
- Histórico em sessão, runtime temporário, dependências separadas e secrets privados.
- Relatórios usa a demonstração DuckDB quando não há configuração PostgreSQL; configuração parcial e falhas de conexão não provocam troca silenciosa de fonte.
- Autenticação, testes de carga, validação clínica e persistência durável não fazem parte do resultado demonstrado.

## OpenRouter — configuração para a demonstração acadêmica

No painel de Secrets do Streamlit, use TOML com valores privados:

```toml
OPENROUTER_MODEL = "google/gemini-2.5-flash-lite"
OPENROUTER_API_KEY = "SUBSTITUA_NO_PAINEL_PRIVADO"
OXICOR_RAG_BACKEND = "local"
OXICOR_ADMIN_PAGES_ENABLED = "false"
OXICOR_OBSERVABILITY_ENABLED = "false"
OXICOR_LANGFUSE_ENABLED = "false"
```

Este bloco informa o modelo utilizado na demonstração e contém somente um placeholder para a chave. Insira sua credencial apenas no painel privado. Não há modelo pago escolhido automaticamente. Não copie a chave para o repositório, relatório ou conversa.

`OPENROUTER_MODEL` e `OPENROUTER_API_KEY` têm prioridade sobre o perfil `CREWAI_*`, inclusive quando apenas um estiver preenchido: uma configuração incompleta bloqueia o chat em vez de usar o Ollama por engano. O endpoint é fixo em `https://openrouter.ai/api/v1`. O código acrescenta `openai/` ao ID para selecionar o adaptador compatível do CrewAI; isso não muda o endpoint para OpenAI. Os testes locais verificam a configuração; somente um teste real poderá comprovar a compatibilidade com o modelo selecionado.

Crie uma chave exclusiva para esta demonstração, com teto de crédito total no painel OpenRouter e recarga automática desativada. O limite da chave precisa ser aplicado no provedor: o controle local de solicitações é compartilhado, não limita dólares e pode ser reiniciado junto ao armazenamento temporário. Uma pergunta pode fazer várias chamadas. Não habilite rotas/modelos mais caros automaticamente. Preços e taxas devem ser conferidos na compra. Os créditos da demonstração foram configurados pelo responsável e não acompanham o código.

A publicação foi concluída e os exemplos de RAG, dados, ML e Relatórios foram apresentados. O isolamento entre sessões reais permanece pendente de validação. Os resultados anteriores do golden dataset foram obtidos com a configuração anterior e não comprovam o novo modelo.

Referências: https://openrouter.ai/docs/api/api-reference/api-keys/create-keys e https://openrouter.ai/pricing .

## Validação local com OpenRouter — 12/11/2026

Atualização posterior à preparação descrita acima: a conta e a configuração local do OpenRouter foram concluídas pelo responsável. Modelo escolhido: `google/gemini-2.5-flash-lite`. Nenhuma credencial está neste documento.

- Chamada direta de conectividade: HTTP 200, 24 tokens, custo informado pela API de US$ 0,0000051.
- Fluxo real `run_multi_agent` com `consult_local`: pergunta educacional sobre preparo para aferição de pressão arterial; rota RAG; quatro eventos; execução em 17,55 segundos, incluindo importações.
- A resposta preservou a evidência local e citou `OXICOR_RAG_01_HIPERTENSAO_RESUMO.md`, incluindo o parágrafo de repouso e preparo.
- Execução em container temporário com código montado somente para leitura, dados de runtime temporários e observabilidade/Langfuse desativados. Nenhum container existente foi alterado.

Este teste comprova esse fluxo local com o novo provedor. Não equivale à reexecução do golden dataset, à validação de todas as rotas ou à publicação. Este registro é histórico: posteriormente os exemplos de RAG, dados, ML e Relatórios foram apresentados na URL pública, conforme o estado atual no início deste guia.
## Correção de permissões na hospedagem — 12/11/2026

O primeiro teste público falhou em `usage_policy.request_slot`, ao criar o diretório do controle de uso, antes da inferência. O padrão de runtime inferia `/app/data` pela existência de `/app`, o que não garante permissão de escrita na hospedagem. O padrão agora usa o diretório temporário do sistema; `OXICOR_DATA_DIR` continua permitindo configuração explícita. O Dockerfile define `/app/data` explicitamente para preservar seu volume local. O teste de regressão verifica criação real do banco de uso em diretório temporário, sem chamar modelos. Após a atualização, o autor apresentou uma resposta RAG no site. Uma falha posterior no caminho de seeds do DuckDB foi corrigida com resolução relativa ao código; a consulta de sete participantes e os relatórios fictícios foram demonstrados em seguida.
