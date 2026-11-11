# Evidências de controles de segurança do OXICOR

Data da verificação: 2026-11-09

## Contexto e segurança da validação

- Branch verificada: `etapa3-deepeval`.
- A única alteração pré-existente era `RELATORIO_SEGURANCA_LLM.md`, não rastreado; foi preservado sem edição.
- O `.env` local informa `OXICOR_RAG_BACKEND=local` e modelo Ollama local; URL/chaves de Flowise e chaves Langfuse não estavam configuradas nesse arquivo.
- No container antigo ativo, `OXICOR_RAG_BACKEND` e `OXICOR_LANGFUSE_ENABLED` estavam ausentes; o backend RAG cai no padrão local. Flowise URL/chave e chaves Langfuse estavam configuradas. Não foram exibidos nem registrados os valores.
- A exportação Langfuse no código anterior dependia apenas das chaves. A nova versão exige também `OXICOR_LANGFUSE_ENABLED=true`; a variável estava ausente no container antigo.
- Nenhum request real foi feito ao Ollama, Flowise ou Langfuse. Os testes de integração usaram mocks e a suíte foi executada em container efêmero com `--network none` e o workspace montado somente para leitura.
- Os testes usaram dados identificadores fictícios e bancos temporários. Não houve gravação em históricos, traces, bancos de uso ou corpus RAG existentes. Nenhum container antigo foi parado/reiniciado.

## Controles, cenários e resultados

| Controle | Cenário e resultado esperado | Resultado observado |
|---|---|---|
| Minimização antes do processamento e persistência de mensagem nova | Mensagem fictícia com nome rotulado e e-mail: identificadores substituídos; pergunta legítima sobre diabetes preservada. | Teste `test_chat_history_representation_is_masked_before_persistence` passou. A função usada pelo caminho de entrada produziu texto sem os identificadores e manteve “diabetes tipo 2”. |
| Preservação de contexto médico legítimo | Valores de exemplo `HighBP=0`, `BMI=24`, `Age=5`, pressão `120/80` e glicemia não devem ser removidos por parecerem números. | Teste `test_unlabeled_health_numbers_are_not_phone_matches` passou; a string permaneceu igual. |
| Tratamento de identificadores e segredos formatados | E-mail, CPF, telefone brasileiro formatado e segredo fictício rotulado não devem aparecer após sanitização; termos de saúde permanecem. | Teste `test_identifiers_and_secrets_are_redacted_but_health_terms_remain` passou. |
| Filtro lexical, sem bloquear a finalidade | Pergunta legítima sobre diabetes/hipertensão deve passar; pedido de ignorar regras e revelar prompt deve ser recusado antes de chamar o agente. | Testes de escopo e `test_block_prevents_calls` passaram. O teste específico de saúde manteve a pergunta legítima e o caso malicioso foi recusado. É uma camada lexical, não uma defesa completa contra prompt injection. |
| Conteúdo enviado ao Flowise | Payload fictício de consulta deve conter a pergunta já mascarada e manter o contexto de saúde e o ID opaco da sessão. | `test_external_request_payload_is_minimized` passou. Nenhuma chamada HTTP foi feita. |
| Saída em streaming | Identificador dividido entre tokens SSE deve ser detectado antes de armazenar/exibir a resposta final; texto de saúde permanece. | `test_redaction_handles_identifiers_split_across_stream_chunks` passou. O fluxo acumula tokens e só então aplica a redação; fluxos interrompidos não preservam conteúdo parcial. |
| Trace local e callback | Pergunta, evento e resposta fictícios com e-mail, telefone e CPF devem ser mascarados no retorno, callback e registro SQLite. | `test_new_trace_and_callback_are_redacted` passou em banco temporário. Os valores fictícios não apareceram nos campos verificados. |
| Caminho de erro | Exceção contendo e-mail e segredo fictícios não deve registrar a mensagem da exceção; o tipo do erro e pergunta mascarada podem ser mantidos. | `test_error_trace_keeps_only_error_type_and_redacted_question` passou. O trace registrou `ValueError`, sem os valores fictícios. |
| Exportação Langfuse | Com chaves presentes, mas sem opt-in explícito, não deve haver request; payloads explicitamente montados devem mascarar identificadores. | `test_disabled_by_default_even_with_credentials` confirmou zero requests via mock; `test_langfuse_payload_redacts_even_if_called_with_raw_trace` confirmou mascaramento do payload. Caminho com opt-in verdadeiro foi testado via resposta mockada, sem rede real. |
| Retenção e limpeza | Em bancos temporários, limpeza com prazo explícito remove somente chats/traces expirados e os respectivos estados de exportação; sem prazo configurado, nada é removido. | `test_cleanup_is_opt_in_and_only_deletes_expired_records_in_temp_databases` removeu um registro expirado de cada tipo e preservou os recentes. O prazo de 30 dias foi apenas dado de teste, não uma política do projeto. |
| Renderização da interface | Não permitir HTML bruto do modelo como HTML executável. | Renderização existente com `unsafe_allow_html=False` foi mantida; nenhuma alteração para aceitar HTML foi introduzida. Links Markdown ainda podem direcionar usuários a sites enganosos. |

## Regressão e integridade de artefatos

- Suíte geral de regressão: o registro anterior foi de **43 testes aprovados**, executada por `unittest` em container efêmero sem rede. O resultado veio da descoberta ampla de `tests/`, incluindo testes de entrega, DuckDB, ML, roteamento e política de uso; não representa uma suíte exclusivamente de segurança.
- A origem desse total de 43 está confirmada pela execução registrada anteriormente: `docker run --rm --network none --mount "type=bind,source=$repo,target=/work,readonly" -w /work -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/work --entrypoint python streamlit-flowise-chat-chat -m unittest discover -s tests -v`, com saída `Ran 43 tests ... OK`.
- Validação focalizada de segurança: execução manual posterior, informada pelo usuário, reportou **26 aprovados em 3,41 s** usando a imagem `oxicor-clone-chat:latest`. O comando reproduzível está registrado abaixo. Esse total é menor porque seleciona os testes de privacidade, exportação, política de uso e apenas dois testes específicos de regressão (DuckDB e entrega), em vez de descobrir toda a suíte.
- Tentativa com a imagem `streamlit-flowise-chat-chat` para essa seleção `pytest` falhou porque a imagem não continha `pytest`. Essa falha é de ferramenta disponível na imagem, não um teste reprovado. A imagem `oxicor-clone-chat:latest` usada na execução manual tinha `pytest`.
- A contagem 26 e o tempo de 3,41 s são resultado relatado pelo usuário; não foram reexecutados nem verificados de forma independente nesta atualização documental.
- AST/sintaxe dos módulos Python alterados: passou.
- `git diff --check`: passou.
- Arquivos do golden dataset e evidências anteriores de `evaluation/` não foram alterados.
- DeepEval/golden com inferência real não foi executado: não era necessário para validar a redação, a retenção temporária ou o opt-in de exportação, e a execução poderia invocar inferência/serviços. Não foram alterados critérios, casos ou resultados existentes.
- Uma primeira tentativa de executar parte da regressão no Python do host encontrou dependências ausentes (`duckdb`) e limitações de remoção de SQLite no Windows. A suíte geral foi então executada no container efêmero, sem rede.

### Comando reproduzível para a seleção de segurança

Executar no PowerShell a partir da raiz do repositório. O workspace fica montado somente para leitura, a rede do container é desabilitada, não há `.env` montado nem chamadas a serviços, e os testes criam seus dados fictícios e bancos temporários:

```powershell
$repo = (Get-Location).Path
docker run --rm --network none --mount "type=bind,source=$repo,target=/work,readonly" -w /work -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/work --entrypoint python oxicor-clone-chat:latest -m pytest -q -ra tests/test_privacy_controls.py tests/test_langfuse_export.py tests/test_usage_policy.py tests/test_multi_agents.py::DuckDBTests::test_no_user_sql tests/test_delivery.py::DeliveryTests::test_trace_records_failure_without_exception_message
```

`pytest -ra` exibe separadamente aprovados, reprovados e ignorados. Testes ignorados, se houver, não contam como aprovados. Resultado manual relatado para esse comando: `26 passed in 3.41s`, sem contagem de falhas ou ignorados exibida.

Esta é uma validação automatizada focalizada de funções e caminhos isolados. Ela **não** demonstra uma conversa ponta a ponta na interface Streamlit, comportamento visual de links, disponibilidade do Ollama ou funcionamento real de Flowise/Langfuse. A rede está bloqueada intencionalmente e chamadas externas não são feitas.

## Implementado

- Redação de formatos comuns de e-mail, CPF, telefone formatado, identificadores rotulados e segredos rotulados.
- Aplicação da redação na entrada nova, antes de seguir para o modelo/RAG; no payload de Flowise; na saída final e no stream; em eventos, respostas e traces novos; e no payload Langfuse.
- Redação apenas para exibição de históricos/traces legados; leitura não regrava nem migra esses registros.
- Langfuse desativado por padrão mesmo com chaves presentes; é necessário `OXICOR_LANGFUSE_ENABLED=true` além das credenciais.
- Limpeza local opt-in através de `OXICOR_RETENTION_DAYS`, sem prazo padrão. Ao configurar, a aplicação limpa chats sem atividade e traces locais expirados na inicialização do chat.
- Backend RAG aceita apenas `local` ou `flowise`; configuração ausente usa local, valor inválido falha sem fazer request. Flowise continua opcional e exige selecionar explicitamente o backend.
- Arquivos de implementação incluídos no Dockerfile.

## Dependências de decisão humana

- Definir se e por quanto tempo históricos e traces devem ser retidos; o projeto não recomenda um número de dias.
- Decidir quais pessoas/papéis podem acessar o histórico, a observabilidade e qualquer instância Langfuse. O aplicativo atual não tem autenticação por usuário.
- Avaliar separadamente a hospedagem e o tratamento de dados de cada instância Flowise/Langfuse antes de habilitá-las.
- Definir se conversas podem incluir informações de saúde reais e quais avisos/consentimentos são necessários.

## Riscos residuais e implantação

- A redação é baseada em padrões e rótulos, não em identificação semântica completa. Nomes ou identificadores em texto livre podem não ser detectados; conteúdo mascarado/resumido pode continuar identificável.
- A sanitização não garante anonimização, segurança factual da resposta, resistência completa a prompt injection ou proteção contra phishing por link.
- A configuração opt-in de Langfuse e demais mudanças estão no workspace; o container antigo não foi reconstruído nem reiniciado. Como esse container tem chaves Langfuse configuradas e executa código anterior à nova exigência de opt-in, pode continuar exportando traces enquanto permanecer ativo e receber solicitações. A nova proteção só vale após uma implantação controlada da versão atual.
- Não foram implementadas autenticação por usuário, revisão humana clínica, análise jurídica, retenção em Langfuse, nem controles de hospedagem/infraestrutura de serviços externos.
