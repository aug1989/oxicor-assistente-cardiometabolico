# Evidências da suíte DeepEval OXICOR

Os XMLs desta pasta foram copiados do volume Docker `oxicor-clone_chat_history`, diretório `/app/data/evaluation/deepeval/`. Os arquivos de origem permanecem no volume. Os relatórios de G01 e da nova execução de G11 foram gerados posteriormente e exportados sem substituir as evidências anteriores. Os dados da avaliação legada não foram modificados.

## Resultados anteriores à correção de recuperação RAG

A tabela abaixo consolida os XMLs anteriores à mudança de `local_rag.py`. G01 e os casos não RAG foram executados antes da correção; G08–G13 também tinham resultados anteriores. A repetição de G11 indicada como pré-correção ocorreu antes da alteração e reprovou. Esses resultados não representam uma nova execução completa dos 15 casos após a correção.

Há XMLs para G01–G15. G01 foi executado pelo fluxo real nesta complementação e passou; seu XML está em `G01-result.xml`. Separadamente, `evaluation/golden_results.json` contém um resultado legado aprovado para G01, iniciado em 2026-10-19. Os XMLs G02–G15 são os relatórios das execuções anteriores, e o G11 anterior permanece preservado na raiz desta pasta.

| Caso | Resultado DeepEval | Duração do caso no XML |
|---|---|---:|
| G01 | Aprovado (nova execução real; XML encontrado) | 42,434 s |
| G02 | Aprovado (XML encontrado) | 37,582 s |
| G03 | Aprovado (XML encontrado) | 25,104 s |
| G04 | Aprovado (XML encontrado) | 45,655 s |
| G05 | Aprovado (XML encontrado) | 20,911 s |
| G06 | Aprovado (XML encontrado) | 45,589 s |
| G07 | Aprovado (XML encontrado) | 30,695 s |
| G08 | Aprovado (XML encontrado) | 75,818 s |
| G09 | Aprovado (XML encontrado) | 58,901 s |
| G10 | Aprovado (XML encontrado) | 65,419 s |
| G11 anterior | Reprovado por critério (XML preservado) | 68,470 s |
| G11 repetição pré-correção | Reprovado por critério; evidências detalhadas abaixo | 85,623 s |
| G12 | Aprovado (XML encontrado) | 62,302 s |
| G13 | Aprovado (XML encontrado) | 46,243 s |
| G14 | Aprovado (XML encontrado) | 0,037 s |
| G15 | Aprovado (XML encontrado) | 0,076 s |

Considerando cada execução registrada em XML, são 14 aprovações e duas reprovações por critério: a execução original de G11 e sua nova execução. São 15 casos distintos; G11 aparece duas vezes. Os XMLs dos casos aprovados registram estado e duração, mas não incluem as respostas do aplicativo.

## Rodada após a ampliação contextual do RAG

O trace persistente da execução anterior de G11 mostrou que o parágrafo com os passos de preparo estava no **3º lugar**, com escore TF-IDF **0,1006**. Os dois selecionados tinham escores **0,2328** e **0,1284**. Como o limite era `top_k=2`, o parágrafo ficou fora pelo ranking, não pelo limiar de **0,07**.

Em `local_rag.py`, a recuperação continua ranqueando os mesmos parágrafos, com o mesmo `top_k` e limiar. Agora, para cada trecho escolhido, inclui também os parágrafos imediatamente vizinhos da mesma seção; resultados selecionados da mesma seção são reunidos sem duplicar o contexto. A mudança é geral, não acrescenta conteúdo fixo nem regras específicas de pressão arterial.

A imagem isolada foi reconstruída e, após a correção, executaram-se somente seis casos RAG — G08, G09, G10, G11, G12 e G13 — um por vez, com Ollama local. Todos passaram pelos critérios existentes. Os demais resultados da tabela acima são anteriores à correção; não houve uma nova execução completa dos 15 casos:

| Caso | Resultado | Duração do caso |
|---|---|---:|
| G11 | Aprovado; 3/3 grupos, rota correta, grounding 1,0 | 123,159 s |
| G08 | Aprovado | 82,790 s |
| G09 | Aprovado | 83,527 s |
| G10 | Aprovado | 70,579 s |
| G12 | Aprovado | 70,992 s |
| G13 | Aprovado | 61,224 s |

Na nova execução de G11, o parágrafo de preparo aparece no contexto recuperado, e os grupos `medida`/`medição`, `repouso`/`preparo`/`preparação` e `Fonte:` passaram. O resultado foi relevância **1,0**, grounding **1,0** e aprovação. Isso contrasta com a execução anterior registrada acima, que passou em apenas 2/3 grupos. Os dados completos da resposta, contexto e verificações estão em `rag-context-expansion-run-01/G11-execution.json`.

Verificações sem modelo confirmaram que duas paráfrases lexicais de G11 incluem o parágrafo de preparo; as cinco consultas RAG de outros temas não o receberam. A busca continua lexical: a paráfrase “Como devo me posicionar e descansar antes de aferir a pressão?” ainda não seleciona um trecho da seção de medida. A expansão de vizinhança só ajuda quando um parágrafo relacionado já foi ranqueado; não resolve toda equivalência semântica.

Os seis XMLs e o JSON detalhado desta rodada estão em `rag-context-expansion-run-01/`. Eles são separados dos relatórios anteriores e também foram preservados no volume Docker. A base em `rag/`, o golden dataset e os critérios de `evaluate_golden.py` não foram alterados.

## Análise de G11

**Pergunta:** “Segundo a base OXICOR, como preparar a medida da pressão arterial?”

Na repetição real **pré-correção**, a pergunta foi roteada para `RAG`, como esperado. A resposta e o contexto recuperado estão registrados em `G11-rerun-20261108-2212/G11-execution.json`; o XML correspondente é `G11-rerun-20261108-2212/G11-rerun-20261108-2208-result.xml`. Ela não deve ser confundida com a execução pós-correção, aprovada e documentada na seção anterior.

Os três grupos esperados são:

1. `medida` ou `medição` — **atendido**
2. `repouso`, `preparo` ou `preparação` — **não atendido**
3. `Fonte:` — **atendido**

A nova execução teve rota correta, grounding `1.0`, relevância `0.667` e falhou no critério global porque somente 2 dos 3 grupos foram encontrados. O texto recuperado inclui a seção “Medida adequada” — obter mais de uma leitura, respeitar intervalo e registrar valores e circunstâncias — e “Conceitos essenciais”, sobre definições de PA, PAS, PAD e hipertensão. Embora mencione intervalo e técnica correta, não inclui nenhum termo alternativo do segundo grupo esperado.

Como evidência histórica separada, `evaluation/golden_results.json` contém uma execução legada de G11 iniciada em 2026-10-19. Ela também teve relevância `0.667`, grounding `1.0`, rota `RAG` e verificações `[true, false, true]`. A resposta legada recuperou:

- A seção “Medida adequada” de `OXICOR_RAG_01_HIPERTENSAO_RESUMO.md`, sobre obter mais de uma leitura, respeitar intervalo e registrar valores e circunstâncias.
- A seção “Conceitos essenciais”, com definições de PA, PAS, PAD e hipertensão.

**Melhoria proposta, sem alteração nesta etapa:** verificar se a recuperação RAG seleciona conteúdo que trate explicitamente do repouso e do preparo antes da aferição; se necessário, melhorar a cobertura do corpus ou a recuperação lexical para esses conceitos. Manter intactos os grupos esperados e os critérios existentes, avaliando a mudança contra o mesmo caso.

## Arquivos exportados

Foram exportados, sem sobrescrever o volume original:

`G01-result.xml` e os relatórios anteriores `G02-result.xml`–`G15-result.xml`, além do XML separado da nova execução de G11 e de seu registro detalhado em JSON.

Nenhum `.env`, credencial, dataset golden ou resultado legado foi copiado ou alterado.
