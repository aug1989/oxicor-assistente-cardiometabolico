# Preparação do OXICOR para Streamlit Community Cloud

Este documento descreve a configuração de hospedagem preparada na branch `etapa3-deploy`. **Ainda não há deploy publicado nem URL validada.** O provedor escolhido para preparar o deploy é OpenRouter. A conta, a chave e o modelo ainda precisam ser configurados e validados; não houve chamada real nesta preparação. O aplicativo não substitui essa configuração por respostas simuladas.

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
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Não | Habilitam Relatórios. Aponte somente para PostgreSQL preparado com dados fictícios e permissões de leitura. Sem essa configuração, a página informa que o serviço não está disponível. |
| `OXICOR_DATA_DIR` | Não | Diretório gravável dos arquivos transitórios. O padrão é `/tmp/oxicor` na hospedagem; no Docker local permanece `/app/data`. O armazenamento Community Cloud é efêmero. |
| `OXICOR_DUCKDB_PATH` | Não | Substitui o caminho do banco DuckDB reconstruído dos CSVs de demonstração. |
| `OXICOR_ADMIN_PAGES_ENABLED` | Não; padrão `false` | Expõe as páginas Observabilidade e Avaliação. Não habilite numa publicação pública sem autenticação e revisão de acesso. |
| `OXICOR_OBSERVABILITY_ENABLED` | Não; padrão `false` | Habilita persistência local transitória de traces. Desativado, os traces não são gravados nem exportados pelo fluxo de atendimento. |
| `OXICOR_LANGFUSE_ENABLED` | Não; padrão `false` | Integração externa opcional. Exige habilitação explícita, chaves e URL; não configure enquanto o destino e o tratamento de dados não forem aprovados. |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | Não | Secrets da integração Langfuse opt-in. |
| `FLOWISE_API_URL`, `FLOWISE_API_KEY` | Não | Configuração opcional do backend RAG Flowise. |

O modelo OpenRouter e sua chave ainda não estão configurados para o Community Cloud nesta etapa. A interface avisa que o chat depende do par `OPENROUTER_MODEL`/`OPENROUTER_API_KEY` ou da configuração alternativa `CREWAI_*`; ao enviar uma pergunta sem essas definições, apresenta indisponibilidade, sem chamar um modelo ou fabricar resposta.

## Dados, histórico e arquivos graváveis

- Conversas e IDs de sessão Flowise permanecem somente em `st.session_state`, isolados por sessão Streamlit. O app não carrega nem grava o histórico compartilhado SQLite anterior. Uma nova sessão ou reinicialização pode perder o histórico; não há garantia de persistência.
- Os bancos, resultados de execução e arquivos de treinamento graváveis usam `OXICOR_DATA_DIR` ou caminhos substituíveis por configuração. Os arquivos temporários do Community Cloud não são armazenamento durável e podem ser removidos em reinicialização ou suspensão.
- O DuckDB é inicializado sob demanda a partir dos CSVs disponíveis no repositório. O app também usa o corpus Markdown local, o modelo preditivo já versionado e o dataset CDC público.
- A página de Relatórios só funciona depois de conectar o PostgreSQL. Antes da publicação, confirme que todas as linhas disponibilizadas são fictícias e que as credenciais têm permissão somente de leitura.
- Não configure dados reais de saúde ou identificação. O mascaramento existente é best-effort e não garante anonimização.
- O arquivo SQLite de histórico e os volumes/container antigos não foram apagados, migrados ou transformados por esta preparação. O código novo simplesmente não carrega esse histórico para as sessões do app.

## Páginas e segurança

Chat, Relatórios e ML Tradicional continuam no menu. Relatórios depende do PostgreSQL; treinamento de ML e o carregamento de bibliotecas podem exceder os recursos gratuitos, então precisam de validação prática.

Observabilidade e Avaliação continuam implementadas, mas ficam fora do menu por padrão. A página de traces não deve ser exposta a visitantes sem autenticação: traces podem conter perguntas e respostas, mesmo após mascaramento. Para testar localmente em ambiente controlado, habilite as flags correspondentes; não habilite as páginas administrativas em uma instância pública aberta. Langfuse também permanece desativado por padrão.

O histórico por sessão reduz a exposição entre sessões do app, mas não é autenticação nem mecanismo para armazenar dados clínicos. Exiba orientação para usar somente exemplos fictícios.

## Limitações confirmadas e validações pendentes

**Confirmado pela documentação consultada:** o Community Cloud executa apps Streamlit a partir do repositório, instala dependências Python/Linux por seus arquivos próprios e suspende apps após período sem tráfego. A documentação informa aproximadamente até 2 cores e 2,7 GB de RAM, valores sujeitos a mudanças. Verifique os [recursos e suspensão](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app#app-sleeping) no momento do deploy.

**Ainda precisa de teste no Community Cloud:** instalação de todas as dependências; memória e tempo de inicialização; disponibilidade do artefato sklearn e inicialização DuckDB; funcionamento da página ML; conexão a PostgreSQL fictício; isolamento entre duas sessões reais; configuração CrewAI com o modelo OpenRouter escolhido; latência, quota, cobrança, termos e tratamento de dados desse provedor. Nenhum desses pontos é comprovado pelos testes locais de unidade.

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

## Estado desta preparação

- **Implementado:** caminhos graváveis configuráveis; dependências de runtime e teste separadas e com versões diretas fixadas; pacote Linux; secrets/variáveis centralizados; histórico em sessão; traces desativados por padrão; páginas globais administrativas escondidas por padrão; aviso e erro claros quando a configuração de IA não existe.
- **Pendente:** configuração e validação do OpenRouter; decisão sobre PostgreSQL para Relatórios; validação de build e recursos na plataforma; eventual autenticação antes de expor páginas administrativas; smoke test completo numa URL pública.
- **Não feito:** deploy, contratação/ativação de serviço, chamadas pagas, alteração de containers ou limpeza de histórico/evidências existentes.


## OpenRouter — configuração para a demonstração acadêmica

No painel de Secrets do Streamlit, use TOML com valores privados:

```toml
OPENROUTER_MODEL = "fabricante/modelo-escolhido"
OPENROUTER_API_KEY = "SUBSTITUA_NO_PAINEL_PRIVADO"
OXICOR_RAG_BACKEND = "local"
OXICOR_ADMIN_PAGES_ENABLED = "false"
OXICOR_OBSERVABILITY_ENABLED = "false"
OXICOR_LANGFUSE_ENABLED = "false"
```

Este bloco contém placeholders, não é uma configuração pronta para inferência. Escolha um ID real no catálogo OpenRouter antes de usar. Não há modelo pago escolhido automaticamente. Não copie a chave para o repositório, relatório ou conversa.

`OPENROUTER_MODEL` e `OPENROUTER_API_KEY` têm prioridade sobre o perfil `CREWAI_*`, inclusive quando apenas um estiver preenchido: uma configuração incompleta bloqueia o chat em vez de usar o Ollama por engano. O endpoint é fixo em `https://openrouter.ai/api/v1`. O código acrescenta `openai/` ao ID para selecionar o adaptador compatível do CrewAI; isso não muda o endpoint para OpenAI. Os testes locais verificam a configuração; somente um teste real poderá comprovar a compatibilidade com o modelo selecionado.

Crie uma chave exclusiva para esta demonstração, com teto de crédito total no painel OpenRouter e recarga automática desativada. O limite da chave precisa ser aplicado no provedor: o controle local de solicitações é compartilhado, não limita dólares e pode ser reiniciado junto ao armazenamento temporário. Uma pergunta pode fazer várias chamadas. Não habilite rotas/modelos mais caros automaticamente. Preços e taxas devem ser conferidos na compra; nenhum crédito foi adquirido por esta preparação.

A publicação continua pendente de instalação limpa, configuração da conta/modelo, uma chamada com pergunta fictícia e verificação de RAG, dados, ML e isolamento entre sessões. Os resultados anteriores do golden dataset foram obtidos com a configuração anterior e não comprovam o novo modelo.

Referências: https://openrouter.ai/docs/api/api-reference/api-keys/create-keys e https://openrouter.ai/pricing .

## Validação local com OpenRouter — 12/11/2026

Atualização posterior à preparação descrita acima: a conta e a configuração local do OpenRouter foram concluídas pelo responsável. Modelo escolhido: `google/gemini-2.5-flash-lite`. Nenhuma credencial está neste documento.

- Chamada direta de conectividade: HTTP 200, 24 tokens, custo informado pela API de US$ 0,0000051.
- Fluxo real `run_multi_agent` com `consult_local`: pergunta educacional sobre preparo para aferição de pressão arterial; rota RAG; quatro eventos; execução em 17,55 segundos, incluindo importações.
- A resposta preservou a evidência local e citou `OXICOR_RAG_01_HIPERTENSAO_RESUMO.md`, incluindo o parágrafo de repouso e preparo.
- Execução em container temporário com código montado somente para leitura, dados de runtime temporários e observabilidade/Langfuse desativados. Nenhum container existente foi alterado.

Este teste comprova esse fluxo local com o novo provedor. Não equivale à reexecução do golden dataset, à validação de todas as rotas ou à publicação. A instalação limpa e os testes na URL pública continuam pendentes. As referências acima a ausência de chamadas reais descrevem o estado anterior a esta atualização.