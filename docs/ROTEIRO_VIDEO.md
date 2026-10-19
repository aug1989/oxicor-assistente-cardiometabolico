# Roteiro de demonstração OXICOR

Duração sugerida: 4 minutos. Use dados fictícios. O processamento local pode demorar; se cortar a espera na edição, sinalize o corte e mantenha visível o resultado verdadeiro.

## 0:00 a 0:30 — O desafio

“Meu projeto é o OXICOR, um assistente educacional de saúde cardiometabólica. O desafio é reunir consulta a dados, classificação de um perfil e recuperação de informações em uma interface acessível. Nesta etapa, integrei o modelo de aprendizado de máquina, agentes especializados, monitoramento e testes. O sistema não faz diagnóstico.”

Mostre o Chat e o menu lateral.

## 0:30 a 1:35 — Modelo integrado ao chat

Envie este perfil fictício no Chat:

```text
Previsão de diabetes para perfil fictício: HighBP=0; HighChol=0; CholCheck=1; BMI=24; Smoker=0; Stroke=0; HeartDiseaseorAttack=0; PhysActivity=1; Fruits=1; Veggies=1; HvyAlcoholConsump=0; AnyHealthcare=1; NoDocbcCost=0; GenHlth=2; MentHlth=0; PhysHlth=0; DiffWalk=0; Sex=1; Age=5.
```

Mostre o agente ativo e depois abra “Ver handoffs e respostas dos agentes”.

“O especialista ML consulta o modelo salvo. O condensador organiza a resposta sem alterar a evidência. Age é uma categoria do dataset, não idade em anos. O resultado é uma classificação do alvo do conjunto de dados, não uma previsão de doença futura.”

Na área ML Tradicional, mostre as cinco métricas do modelo ativo.

“O teste separado apresentou recall de 80,6%, precisão de 29,5% e ROC-AUC de 0,826. Priorizei sensibilidade no experimento, mas a baixa precisão exige explicitar os falsos positivos e limita o uso à demonstração educacional.”

## 1:35 a 2:15 — Ferramentas e agentes

Mostre uma execução concluída da pergunta “Quantos participantes há na base OXICOR?” e uma da pergunta “Segundo a base OXICOR, uma glicemia isolada confirma ou exclui diabetes?”. Elas ficam na Observabilidade e na Avaliação.

“A triagem por regras encaminha a pergunta. O especialista DuckDB só acessa consultas fixas de leitura. O especialista RAG recupera trechos dos resumos locais e identifica suas fontes. Há cinco papéis definidos; apenas os necessários participam de cada solicitação. A saudação e a recusa fora do escopo não consomem uma chamada ao modelo.”

## 2:15 a 2:50 — Observabilidade

Abra o Langfuse, projeto triagem, e mostre cinco execuções OXICOR chat. Abra uma execução para mostrar a pergunta, ferramentas, especialistas, condensador, duração e uso de tokens. A área Observabilidade do Streamlit também mantém o registro local.

“Integrei o Langfuse ao fluxo CrewAI e Ollama usado pelo Streamlit. Aqui aparecem os registros de execuções reais, com ferramentas, especialistas, respostas verificadas, duração e tokens. O registro local em SQLite continua disponível. A tarifa de API do modelo local é zero; isso não significa ausência de custos de energia e hardware.”

## 2:50 a 3:30 — Avaliação

Abra Avaliação e mostre as 15 perguntas e o resultado realmente exibido.

“Das quinze perguntas, quatorze passaram. Uma recuperou informações incompletas sobre preparo para medir a pressão. A suíte executa as perguntas no mesmo fluxo do chat, com CrewAI e Ollama. Verifica rota, presença de fatos esperados e preservação das evidências. É um equivalente local com critérios determinísticos publicados, não DeepEval. Esses critérios ajudam a detectar regressões, mas não garantem validade clínica ou equivalência semântica completa.”

Abra o caso G11 e mostre que a avaliação identificou a recuperação incompleta. Explique que preservar a fonte não garante responder completamente à pergunta.

## 3:30 a 4:10 — Reflexão pessoal

Adapte este trecho para refletir sua experiência:

“A integração de Docker, Ollama e agentes exigiu atenção ao ambiente e ao consumo de recursos. Aprendi que testes de código não substituem a execução real das perguntas. Também precisei separar classificação de diagnóstico, retirar o identificador do treino e registrar todas as métricas. O próximo passo é revisar as fontes científicas originais, ampliar a avaliação semântica e validar a segurança antes de disponibilizar o sistema a outras pessoas.”

## Antes de enviar

- Confira se o vídeo tem entre 3 e 5 minutos e se a voz está audível.
- Mostre resultados reais, sem incluir o arquivo `.env` na gravação.
- Revise o relatório e personalize sua reflexão.
- Envie o código/repositório, o relatório e o vídeo conforme as instruções da disciplina.
