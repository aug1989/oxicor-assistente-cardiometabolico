# Relatório técnico OXICOR Etapa 2

## Desafio e investigação

O OXICOR é um assistente educacional de saúde cardiometabólica. A pergunta essencial do projeto é como transformar dados de triagem e conhecimento científico em informações acessíveis sobre fatores de risco. Na fase Investigar do CBL, o desafio foi conectar um modelo de classificação, agentes com ferramentas restritas e mecanismos de monitoramento e teste em um mesmo chat. A interface Streamlit reúne as camadas e apresenta sua origem ao usuário. A execução descrita neste relatório ocorreu em 19 de outubro de 2026, em ambiente local com Docker e Ollama. O sistema não substitui avaliação profissional.

## Dataset e preparação

Foi utilizado o CDC Diabetes Health Indicators, disponibilizado pelo UCI Machine Learning Repository, DOI 10.24432/C53919. A cópia utilizada contém 253.680 registros e 35.346 exemplos positivos. O alvo Diabetes_binary diferencia ausência de diabetes da classe diabetes ou pré-diabetes, conforme a documentação do UCI [1]. Esse problema conecta-se ao domínio cardiometabólico por reunir indicadores de saúde e hábitos associados ao alvo observado. Trata-se de classificação transversal; o dataset não sustenta uma previsão temporal individual de desenvolvimento futuro da doença.

O treinamento utiliza 19 preditores, incluindo pressão elevada, colesterol, IMC, atividade física e faixa etária. Foram excluídos ID, variável-alvo, Education e Income. O identificador não representa uma característica preditiva pertinente. A exclusão das duas variáveis socioeconômicas delimita este experimento e não elimina vieses. Age utiliza categorias, e Smoker representa histórico de pelo menos 100 cigarros na vida, não necessariamente tabagismo atual. Essas codificações precisam ser respeitadas nas entradas.

Perfis idênticos, considerando os preditores utilizados, foram mantidos na mesma partição para reduzir contaminação entre treino e teste. GroupShuffleSplit, com sementes 42 e 43, produziu 177.303 registros de treino, 38.500 de validação e 37.877 de teste. O artefato registra parâmetros, versões, índices das partições e hash do CSV. O modelo anterior foi preservado localmente; a inferência passou a priorizar o artefato reproduzível da etapa 2.

## Modelo e interpretação das métricas

Foi treinado um HistGradientBoostingClassifier do scikit-learn 1.7.2, com 120 iterações, até 15 folhas e taxa de aprendizado 0,08. A escolha oferece uma implementação disponível no ambiente, reproduzível e adequada a relações não lineares em dados tabulares; não representa uma demonstração de superioridade sobre todos os algoritmos. O limiar foi escolhido exclusivamente na validação: entre 0,05 e 0,50, em passos de 0,01, selecionou-se a maior precisão com recall de pelo menos 0,80. O limiar resultante foi 0,13.

| Métrica no teste separado | Valor |
|---|---:|
| Accuracy | 70,55% |
| Precision | 29,55% |
| Recall | 80,56% |
| F1 | 43,24% |
| ROC-AUC | 0,8259 |

O recall foi priorizado para investigar a identificação da classe positiva no contexto educacional. Entretanto, a precisão de 29,55% evidencia muitos falsos positivos. A matriz de confusão contém 4.248 verdadeiros positivos, 1.025 falsos negativos, 10.129 falsos positivos e 22.475 verdadeiros negativos. Um classificador que respondesse sempre negativo teria aproximadamente 86,1% de acurácia, mas recall zero; isso mostra por que acurácia isolada seria enganosa. F1 sintetiza o compromisso entre precisão e recall, enquanto ROC-AUC avalia discriminação entre limiares. Não foram demonstradas calibração individual, validade externa no Brasil ou utilidade clínica.

## Agentes e ferramentas

| Agente | Papel e acesso |
|---|---|
| Genérico | Orientação sobre o OXICOR, sem ferramenta externa |
| Especialista DuckDB | Agregações fixas em banco somente leitura |
| Especialista ML | Inferência com o modelo salvo e indicação de dados faltantes |
| Especialista RAG | Recuperação de trechos e identificação de fontes locais |
| Condensador | Organização dos blocos verificados, sem ferramenta |

CrewAI 1.15.25 executa as tarefas com o modelo local qwen3:4b-instruct-oxicor-cpu. O encaminhamento é feito por regras e pode selecionar mais de um especialista. A ferramenta é executada obrigatoriamente pelo orquestrador; os agentes não recebem delegação irrestrita. O especialista recebe o resultado, e alterações indevidas são substituídas pela evidência original. O condensador propõe somente a ordem dos blocos. Essa restrição favorece rastreabilidade, embora reduza a liberdade de síntese. O chat mostra agente ativo, eventos e respostas em Markdown.

O RAG desta entrega usa TF-IDF para recuperar até dois trechos de três resumos locais sobre hipertensão, obesidade e diabetes. O texto é preservado e acompanhado de arquivo e seção. A integração anterior com Flowise permanece opcional. A recuperação lexical pode perder sinônimos ou selecionar contexto insuficiente. As referências declaradas nos resumos ainda precisam de conferência integral nas fontes originais; a identificação do arquivo não equivale à validação científica do conteúdo.

## Observabilidade

Foi implementado um equivalente local de observabilidade em SQLite, apresentado na área Observabilidade do Streamlit. Cada solicitação recebe identificador, horário UTC, duração, status, rota e eventos de ferramentas e agentes. O uso de tokens é registrado quando informado pelo provedor. O painel permite exportar JSON e inspecionar uma execução. Foram exportados 15 registros reais, incluindo 13 execuções concluídas com agentes. A captura anexa mostra pelo menos cinco traces. Não se trata de uma instalação do Langfuse. O processamento local não tem tarifa de API de LLM; energia e hardware não foram contabilizados.

## Golden dataset e testes

A suíte equivalente local executou 15 perguntas predefinidas no mesmo fluxo CrewAI do chat: consultas de dados, solicitação incompleta de ML, perfil fictício completo, recuperação científica, saudação e recusa fora do escopo. Os resultados foram 14 aprovações em 15 casos; casos que exigem revisão: G11. Cada aprovação exige rota correta e cobertura de todos os grupos de termos esperados. A relevância corresponde à fração desses grupos presentes. O grounding verifica preservação integral das evidências das ferramentas; sem ferramenta, é não aplicável.

Essas medidas são proxies determinísticos de regressão, não avaliação semântica completa por juiz LLM. A preservação textual é favorecida pela própria arquitetura e não comprova a correção clínica dos trechos. A suíte não utiliza DeepEval e sua metodologia está publicada no código. Separadamente, 34 testes técnicos passaram, cobrindo roteamento, consultas restritas, limites de uso, preservação de evidências, observabilidade e inferência. Resultados e capturas acompanham a entrega, sem substituir a análise crítica por uma alegação genérica de qualidade.

## Limitações e próximos passos

A investigação mostrou que integração funcional exige verificar o ambiente, executar perguntas reais e examinar métricas além da acurácia. O sistema limita entradas a 3.000 caracteres, admite uma solicitação por vez e aplica quotas compartilhadas de 30 por hora e 100 por dia, com intervalo de 15 segundos. O filtro lexical de escopo é limitado e não garante resistência a toda tentativa de desvio. O histórico é local e não possui isolamento por usuário. Os próximos passos são revisar fontes, ampliar avaliações semânticas e adversariais, validar o modelo externamente e implementar autenticação e proteção de dados antes da publicação prevista na etapa 3.

## Análise dos resultados e reprodutibilidade

O resultado agregado de quatorze aprovações não significa que todas as respostas sejam completas ou clinicamente adequadas. No caso G11, a pergunta solicitava preparação para medir a pressão arterial. O recuperador apresentou informações sobre leituras repetidas e conceitos de pressão, mas deixou de trazer o trecho de preparo esperado. A rota estava correta e o conteúdo recuperado foi preservado; entretanto, o critério de relevância atingiu somente dois dos três grupos esperados. Essa ocorrência mostra a diferença entre fidelidade ao contexto recuperado e atendimento efetivo à pergunta.

A melhoria indicada é revisar a divisão dos documentos em trechos e a recuperação, acrescentando perguntas com sinônimos e expressões usadas pelo público. A alteração deve ser avaliada novamente com os mesmos casos, mantendo os resultados anteriores para comparação. Mudar os critérios depois de observar uma falha apenas para obter aprovação não demonstraria evolução do sistema. Também será necessário ampliar o conjunto de perguntas, pois quinze exemplos não representam toda a diversidade de dúvidas sobre saúde cardiometabólica.

Na integração do modelo, uma pergunta sem variáveis suficientes deve produzir solicitação de dados, não uma classificação inventada. O teste completo utiliza um perfil explicitamente fictício, preservando a separação entre demonstração acadêmica e avaliação de uma pessoa real. A resposta apresenta classe, escore e limiar utilizados. O escore não deve ser interpretado como probabilidade clínica individual validada, pois não foi realizado estudo de calibração nem avaliação prospectiva em usuários do OXICOR.

A reprodução do experimento depende da mesma cópia do dataset, dos índices de divisão e da versão das bibliotecas. Por isso, o treinamento salva essas informações junto ao modelo. O conjunto de teste permanece separado da escolha do limiar; seus resultados não foram usados para ajustar o ponto de corte. A distribuição desbalanceada do alvo e os numerosos falsos positivos precisam acompanhar qualquer apresentação dos indicadores, evitando selecionar apenas a métrica mais favorável.

Os registros de execução também ajudam a distinguir falhas do ambiente de falhas da aplicação. A disponibilidade do container não garante, isoladamente, que o modelo de linguagem esteja acessível. A demonstração verifica a comunicação com o Ollama e percorre o fluxo real de ferramentas, especialistas e condensação. Essa abordagem complementa os testes técnicos, que verificam comportamentos específicos em condições controladas e não substituem a experiência integrada.

Para a entrega, o vídeo deve mostrar a classificação no chat, a participação dos agentes e as áreas de monitoramento e avaliação. As capturas documentam o estado observado, enquanto os arquivos de resultados permitem conferir os critérios e as respostas. A reflexão final deve reconhecer os limites encontrados e indicar melhorias verificáveis, mantendo o caráter educacional do projeto.


A revisão humana continua necessária nesta etapa.

## Referências e evidências


[1] UCI Machine Learning Repository. CDC Diabetes Health Indicators. DOI 10.24432/C53919. https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators. Consulta em 19/10/2026.

Evidências de execução: metricas_modelo.json, golden_results.json, testes_tecnicos.json e traces.json. Código: https://github.com/aug1989/oxicor-assistente-cardiometabolico. As capturas anexas são da aplicação executada localmente.
