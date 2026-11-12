# OXICOR — Etapa 2

Assistente educacional de saúde cardiometabólica com Streamlit, cinco papéis CrewAI, modelo preditivo integrado, DuckDB somente leitura e recuperação de trechos locais. Não realiza diagnóstico nem prescrição.

## Desafio CBL

Como transformar dados de triagem e conhecimento científico em informações acessíveis sobre saúde cardiometabólica? A fase de investigação testa a integração dessas camadas, mede suas limitações e registra evidências reproduzíveis. A documentação original da etapa 1 permanece em `docs/ETAPA1.md`.

## Arquitetura executada

```text
Chat Streamlit
  -> estado de conversa da sessão Streamlit
  -> filtro de escopo e limites compartilhados
  -> encaminhamento por regras
  -> especialista(s) CrewAI + ferramenta restrita
       Dados: consultas fixas DuckDB
       ML: classificação por modelo salvo
       RAG: TF-IDF por parágrafo, com contexto dos vizinhos na mesma seção
       Genérico: orientação sobre o sistema, sem ferramentas
  -> condensador CrewAI: ordena blocos verificados
  -> resposta Markdown e handoffs somente na sessão
```

Os traces persistentes são opt-in e ficam desativados por padrão. As páginas Observabilidade e Avaliação também ficam ocultas por padrão; não as habilite numa instância pública sem autenticação e revisão de acesso.

Os agentes não têm delegação irrestrita. Cada especialista tem somente sua ferramenta. A ferramenta é executada obrigatoriamente pelo orquestrador; respostas dos especialistas que alterem sua evidência são substituídas pelo texto verificado. O condensador escolhe a ordem dos blocos em JSON, sem reescrever os fatos. Saudações e recusas simples são respondidas por regras, sem LLM.

## Iniciar

1. Instale Docker Desktop e Ollama e mantenha ambos ativos.
2. No Ollama, obtenha `qwen3:4b-instruct` e crie o modelo local com `ollama create qwen3:4b-instruct-oxicor-cpu -f config/Modelfile`.
3. Copie `.env.example` para `.env`. Para o chat local, mantenha `OXICOR_RAG_BACKEND=local` e configure o endereço do Ollama acessível pelo container. O modelo foi testado em CPU.
4. Execute `docker compose up -d --build` ou `start.ps1` no Windows.
5. Abra `http://localhost:8501`.

O inicializador copia o modelo da etapa 2 para o volume apenas quando ainda não existe. As quotas persistem no volume Docker; o histórico novo fica somente na sessão e os traces só persistem se `OXICOR_OBSERVABILITY_ENABLED=true`. Volumes e bancos de execuções anteriores permanecem intactos. Não use `docker compose down -v` se quiser preservar dados do volume.

O chat local usa o corpus em `rag/`. A integração anterior com Flowise permanece opcional com `OXICOR_RAG_BACKEND=flowise`, URL e credencial próprias. A área Relatórios mantém a integração PostgreSQL da etapa 1 e exige esse serviço configurado separadamente. Não é necessário Flowise ou PostgreSQL para os testes do golden dataset desta etapa.

## Modelo e reprodução

O CSV público é o CDC Diabetes Health Indicators, disponível no [UCI](https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators). A cópia tem 253.680 linhas. O alvo `Diabetes_binary` representa diabetes/pré-diabetes no conjunto de dados; não há horizonte temporal de previsão futura.

`train_reproducible.py` remove ID, alvo, Education e Income dos preditores e agrupa perfis idênticos na mesma partição. Usa GroupShuffleSplit com sementes 42 e 43. Treina HistGradientBoostingClassifier e escolhe o limiar na validação, exigindo recall de pelo menos 0,80 e maximizando precision entre os limiares testados. O teste separado é avaliado uma vez.

```sh
docker compose exec -e OMP_NUM_THREADS=2 chat python train_reproducible.py /app/seed/cdc_diabetes_health_indicators.csv /app/data/models/etapa2_retreino
```

O destino diferente preserva o modelo ativo. Metadados, hash do CSV, parâmetros, índices de partição e métricas acompanham o artefato. Execute somente arquivos pickle produzidos por fonte confiável.

| Métrica no teste | Resultado |
|---|---:|
| Accuracy | 0,7055 |
| Precision | 0,2955 |
| Recall | 0,8056 |
| F1 | 0,4324 |
| ROC-AUC | 0,8259 |

O limiar é 0,13. A baixa precisão resulta em muitos falsos positivos. A escolha é um experimento educacional, não uma regra clínica. `Age` é uma categoria, não idade em anos. Não há validação externa ou calibração para uso individual no Brasil.

## Observabilidade e avaliação

As áreas **Observabilidade** e **Avaliação** são administrativas, ocultas por padrão e controladas por `OXICOR_ADMIN_PAGES_ENABLED`. A persistência de traces depende também de `OXICOR_OBSERVABILITY_ENABLED`; Langfuse continua separado, opt-in e desativado por padrão. Habilite essas funções somente em ambiente controlado. A avaliação legada mantém seus critérios determinísticos; a suíte DeepEval é separada e reutiliza esses mesmos critérios.

```sh
python evaluate_golden.py
python -m pytest -ra tests
```

Instale primeiro as dependências de teste de `requirements-test.txt` em ambiente virtual. `evaluate_golden.py` chama o fluxo real e requer um provedor de IA configurado; ele não usa respostas simuladas. O `run_tests.py` executa a suíte geral de regressão; não é uma suíte apenas de segurança. Para executar a seleção focalizada de segurança na imagem histórica que contém `pytest`, use no PowerShell, na raiz do repositório:

```powershell
$repo = (Get-Location).Path
docker run --rm --network none --mount "type=bind,source=$repo,target=/work,readonly" -w /work -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/work -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -e DEEPEVAL_DISABLE_DOTENV=1 -e DEEPEVAL_TELEMETRY_OPT_OUT=YES --entrypoint python oxicor-clone-chat:latest -m pytest -q -ra -p no:cacheprovider tests/test_privacy_controls.py tests/test_langfuse_export.py tests/test_usage_policy.py tests/test_multi_agents.py::DuckDBTests::test_no_user_sql tests/test_delivery.py::DeliveryTests::test_trace_records_failure_without_exception_message
```

O comando não monta `.env`, desabilita a rede e usa testes com dados fictícios e bancos temporários. O resultado manual informado para a imagem `oxicor-clone-chat:latest` foi `26 passed in 3.41s`; não foi reexecutado nesta atualização da documentação. A tentativa equivalente com `streamlit-flowise-chat-chat:latest` não pôde iniciar porque essa imagem não contém `pytest`. Essa contagem focalizada não deve ser confundida com os 43 testes da descoberta geral com `unittest`. Consulte [as evidências de segurança](./evaluation/security_evidence/CONTROLES_LLM_2026-11-09.md) para a origem das contagens, os limites e a distinção em relação à validação ponta a ponta da interface.

A avaliação chama o fluxo real com as 15 perguntas de `evaluation/golden.json`. Mantém os limites globais de uso. Relevância mede cobertura dos grupos de termos esperados; grounding mede preservação integral das evidências; aprovação exige também a rota correta. São proxies determinísticos de regressão, não julgamento semântico completo. Casos sem ferramenta têm grounding não aplicável. A preservação é favorecida pelas restrições arquiteturais e não demonstra capacidade irrestrita do LLM.

O DeepEval foi integrado como uma suíte separada em `evaluation/test_deepeval.py` e instalado somente por `requirements-test.txt`. Ela usa os mesmos casos e chama `run_multi_agent` com a recuperação local real; a métrica customizada reutiliza `evaluate()` sem mudar critérios, resultados ou artefatos da avaliação acima. A métrica é determinística, portanto não chama um juiz LLM, não requer `OPENAI_API_KEY` nem login no Confident AI. A execução dos casos chama o provedor de IA configurado e consome seus limites; não execute a suíte sem selecionar um provedor apropriado.

As imagens de runtime instalam somente `requirements.txt`; não instale dependências de teste nem execute DeepEval no container de produção. Use um ambiente virtual isolado com `requirements-test.txt` para testes. A suíte DeepEval realiza inferência real com o provedor configurado, consome os limites desse provedor e não deve ser executada antes de confirmar que o endpoint e os termos são apropriados. O avaliador não usa Flowise por padrão: as consultas RAG usam o corpus local. Não coloque `.env` no Git.

Resultados ficam no diretório de dados de runtime configurado; no Docker, `/app/data/evaluation/`. Os testes técnicos cobrem limites de uso, roteamento, ferramentas, preservação de evidências, observabilidade e predição. As perguntas reais e os testes técnicos são conjuntos diferentes.

## Limites de uso e segurança

Uma solicitação por vez, intervalo de 15 segundos, 30 solicitações por hora, 100 em 24 horas e até 3.000 caracteres. Os limites são compartilhados entre usuários; falhas admitidas também consomem quota. O filtro lexical de escopo é uma primeira barreira e não impede toda tentativa de desvio. Ollama local não cobra tarifa de API; energia e hardware não estão contabilizados.

O histórico novo é mantido somente na sessão atual, sem banco compartilhado. O app não possui autenticação por usuário; não o exponha publicamente com dados reais de saúde. A aplicação mascara formatos comuns de identificadores antes do envio e exibição; isso é uma mitigação de melhor esforço, não anonimização garantida. Nomes ou dados identificáveis descritos livremente podem não ser detectados. Arquivos de históricos e traces preexistentes não são migrados, alterados ou removidos; o app novo não os lê. As respostas Markdown continuam renderizadas sem HTML bruto (`unsafe_allow_html=False`), mas links externos ainda podem ser enganosos. Os resumos RAG têm referências declaradas que ainda requerem conferência nos documentos originais. Veja [Preparação para Streamlit Community Cloud](./docs/DEPLOY.md) para limitações e passos antes de publicar.

## Entrega

- `docs/RELATORIO_ETAPA2.md`: relatório técnico.
- `docs/ROTEIRO_VIDEO.md`: roteiro para demonstração de 3 a 5 minutos.
- `docs/ARQUITETURA_AGENTES.md`: papéis e ferramentas.
- `evaluation/`: golden dataset, resultados de execução e evidências selecionadas.
- `evaluation/security_evidence/`: cenários e resultados dos controles de privacidade adicionados.
- `tests/`: testes técnicos.

Nenhuma credencial `.env`, histórico de conversas ou banco de uso deve ser versionado. Os CSVs pequenos de triagem e participantes são os exemplos de teste já presentes na etapa 1.

### Langfuse

Configure `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL` por variável de ambiente ou secret do Streamlit e defina `OXICOR_LANGFUSE_ENABLED=true` somente se a organização optar por habilitar essa integração. Além disso, a gravação de traces requer `OXICOR_OBSERVABILITY_ENABLED=true`. A integração fica desativada por padrão, mesmo que as chaves estejam presentes. Nunca versione o `.env` ou `secrets.toml`. Recrie o container após alterar o ambiente. A exportação só é tentada quando a habilitação explícita, as duas chaves e o endpoint HTTPS estão presentes; falhas não interrompem o chat. Langfuse pode estar hospedado localmente, em rede privada ou em serviço remoto; confirme a topologia e a política do destino antes de habilitá-lo.

Quando habilitada, a exportação inclui pergunta, resposta e eventos do trace após mascaramento dos formatos de identificadores reconhecidos pela aplicação. O mascaramento é uma mitigação de melhor esforço: não garante anonimização e não detecta todo dado pessoal em texto livre. O registro inclui a resposta verificada da aplicação, não o raciocínio interno do modelo. Os tokens de chamadas sucessivas são separados para evitar dupla contagem do acumulado CrewAI. A tarifa zero indica somente a API Ollama local; não inclui infraestrutura. Não ative a integração com dados reais sem revisar payload, destino, acesso e retenção.

As evidências Langfuse acompanham o relatório entregue separadamente; traces e capturas não são publicados no repositório. Cinco consultas reais incluem uma solicitação composta de DuckDB e RAG. Os testes de unidade devem ser executados com `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` vazios, evitando exportar registros simulados.


### Preparação OpenRouter para o deploy

O deploy aceita `OPENROUTER_MODEL` (ID do catálogo) e `OPENROUTER_API_KEY` nos Secrets privados do Streamlit. O modelo e a conta ainda precisam ser configurados e testados com uma chamada real. Consulte [o guia de deploy](docs/DEPLOY.md#openrouter--configuração-para-a-demonstração-acadêmica). A alternativa local anterior permanece disponível via `CREWAI_*`.
