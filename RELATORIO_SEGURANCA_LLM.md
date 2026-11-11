# Relatório de avaliação de riscos de segurança do uso de LLM no OXICOR

## Escopo e método

Este relatório analisa o código atual do OXICOR com foco em:

- configuração padrão do projeto, configuração verificada e comportamento observado;
- entrada antes do envio ao modelo;
- processamento e observabilidade;
- saída gerada pelo modelo e entrega à interface;
- persistência local e integrações opcionais;
- limites arquiteturais e riscos identificáveis sem executar ataques ou implementar controles.

A revisão foi feita sobre os artefatos observados no repositório atual, especialmente: `app.py`, `multi_agents.py`, `usage_policy.py`, `observability.py`, `langfuse_export.py`, `local_rag.py`, `README.md`, `.env.example` e `compose.yaml`.

## 1) Evidências de configuração e execução

### 1.1 Configuração padrão do projeto

O projeto estabelece uma configuração padrão que aponta para execução local com Ollama:

- `.env.example` define `CREWAI_LLM=ollama/qwen3:4b-instruct-oxicor-cpu`.
- `.env.example` define `CREWAI_BASE_URL=http://host.docker.internal:11434`.
- `.env.example` define `CREWAI_API_KEY=ollama`.
- `README.md` descreve o chat local usando o corpus em `rag/` e menciona Flowise como opcional.
- `multi_agents.py` usa `base = os.getenv('CREWAI_BASE_URL', 'http://host.docker.internal:11434')` e cria `LLM(..., base_url=base, api_key=os.getenv('CREWAI_API_KEY', 'ollama'))`.

Isso indica a configuração padrão de projeto, mas não prova que o ambiente em execução tem o serviço local ativo e acessível em cada sessão.

### 1.2 Configuração verificada vs. comportamento observado

A revisão distingue três níveis:

1. Configuração padrão: o que está escrito no código e nos arquivos de ambiente.
2. Configuração verificada: o que está de fato definido em variáveis de ambiente e serviços disponíveis no ambiente em uso.
3. Comportamento observado: o que o código efetivamente executa em tempo de execução.

No código atual, o comportamento observado é:

- `app.py` usa `OXICOR_RAG_BACKEND` para decidir entre `local_rag` e `flowise_tokens()`.
- `flowise_tokens()` só é chamado quando o backend não é local ou quando a rota de execução exige o fluxo externo.
- `langfuse_export.py` só exporta para Langfuse quando `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` estão configurados e `export_trace()` é chamado.
- `observability.py` grava traces locais em SQLite independentemente da configuração externa.

Esses caminhos demonstram a existência de integrações opcionais, mas não permitem inferir que há envio externo em todos os casos.

### 1.3 Diferenciação de serviço separado e serviço externo

O código distingue entre:

- serviço separado da aplicação: um serviço em processo próprio, como Ollama em Docker ou um endpoint local acessível pela aplicação;
- serviço externo à máquina ou organização: um host remoto, provedores cloud, ou endpoint fora do ambiente local/organizacional.

A aplicação o OXICOR pode se comunicar com serviços separados em dois cenários:

- Ollama local via `http://host.docker.internal:11434` ou outra URL local;
- Flowise/Langfuse em configuração local, em rede privada, ou em provedores remotos.

A presença de `FLOWISE_API_URL` e `LANGFUSE_BASE_URL` não permite afirmar serviço externo ativo nem a natureza do host. O código não especifica onde o serviço está hospedado em todas as implantações.

### 1.4 Filtro de escopo observado

O filtro de escopo implementado no projeto é lexical e baseado em regras de domínio e negação. A evidência está em `usage_policy.py`:

- `scope_reply()` normaliza o texto, limita comprimento e utiliza `re.fullmatch()` e `re.search()` sobre listas de palavras e domínios permitidos.
- `guarded_request()` chama `scope_reply()` e, se o texto não for admitido, retorna `CONTROLE DE USO` sem invocar o agente.

A documentação do README também menciona que esse filtro é “uma primeira barreira e não impede toda tentativa de desvio”. Isso é uma observação de limitação, não uma garantia completa.

## 2) Classificação dos riscos

A revisão do relatório foi reorganizada em três categorias:

- Fatos observados
- Vulnerabilidades demonstradas
- Riscos potenciais

### 2.1 Fatos observados

1. O sistema grava histórico e respostas locais em SQLite.
   - Evidência: `app.py`, `save_chat()` e `load_history()`; `database()` cria a tabela `chats` com colunas `id`, `title`, `session_id`, `messages` e `created_at`.

2. O sistema grava traces locais de observabilidade em SQLite.
   - Evidência: `observability.py`, `database()` cria a tabela `traces` e `observed_request()` persiste `question`, `answer`, `events`, `route` e `status`.

3. O código oferece integração opcional com Flowise e Langfuse.
   - Evidência: `.env.example`, `app.py` e `langfuse_export.py`.

4. O projeto usa recuperação local em arquivos Markdown (`local_rag.py`) como backend padrão.
   - Evidência: `local_rag.py` e `README.md`.

5. O filtro de escopo é lexical e não constitui garantia completa.
   - Evidência: `usage_policy.py` e `README.md`.

6. O render da interface usa `st.markdown(..., unsafe_allow_html=False)`.
   - Evidência: `app.py`, `st.markdown` em renderização de mensagens.

7. O projeto declara que não realiza diagnóstico nem prescrição.
   - Evidência: `README.md` e `app.py`.

### 2.2 Vulnerabilidades demonstradas

Abaixo estão apenas riscos que encontram suporte direto no código e que não dependem de hipótese externa não verificada.

#### 2.2.1 Persistência local de dados sensíveis sem mascaramento explícito

- Evidência no código:
  - `app.py` → `save_chat()`: salva `messages` em SQLite.
  - `observability.py` → `observed_request()`: salva `question`, `answer`, `events` e `route` em SQLite.
  - `langfuse_export.py` → `export_trace()`: envia traces quando as chaves são configuradas.

- Observação:
  - O código grava o conteúdo da conversa e da resposta, e não há mascaramento explícito antes de persistência no trecho observado.
  - Resumos e dados mascarados ainda podem conter informações identificáveis, porque a remoção de partes do texto não garante anonimização completa se o contexto restante for suficiente para identificar a pessoa ou o caso.

- Classificação:
  - Vulnerabilidade demonstrada como risco de exposição de dados e retenção.

- Por que importa:
  - O assistente trata de saúde cardiometabólica; mesmo quando o uso é educacional, um histórico ou trace pode conter dados clínicos, sintomas, contextos pessoais e identificadores indiretos.

- Tratamento proposto:
  - Mineração de dados mínima e mascaramento antes da persistência.
  - Política de retenção e exclusão definida.
  - Acesso restrito aos bancos locais.
  - Documentar o que fica local e o que pode ser exportado.

- Prioridade:
  - Alta.

- Teste de aceitação:
  - Usar um dado fictício de exemplo (por exemplo, “Paciente Joana, CPF 123...”) em um arquivo temporário de teste ou conversa isolada, e verificar que o conteúdo salvo em SQLite foi mascarado ou removido antes do armazenamento, sem contaminar o corpus real.

#### 2.2.2 Exportação opcional de observabilidade para Langfuse sem revisão de conteúdo

- Evidência no código:
  - `langfuse_export.py` → `configured()`, `payload()`, `export_trace()`.
  - `observability.py` → `observed_request()` chama `export_trace()` em bloco `try/except` sem impedir a execução local.

- Observação:
  - Quando as variáveis `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` estiverem preenchidas, o projeto tenta publicar o trace para Langfuse.
  - A exportação não é prova de serviço externo ativo em todos os ambientes; porém, em ambiente configurado, a exportação existe como caminho de envio externo.

- Classificação:
  - Vulnerabilidade demonstrada como risco de exportação externa quando configurado.

- Por que importa:
  - O serviço de observabilidade pode estar fora do ambiente do projeto, e a aplicação pode enviar perguntas/respostas e metadados sem revisão explícita do conteúdo.

- Tratamento proposto:
  - Exportar somente metadados mínimos e respostas já mascaradas.
  - Exigir opt-in explícito para exportação com revisão de dados enviados.
  - Separar o conteúdo do atendimento do conteúdo de telemetria.

- Prioridade:
  - Alta quando a integração estiver habilitada.

- Teste de aceitação:
  - Em um ambiente de teste isolado, configurar Chaves Langfuse em um endpoint temporário e verificar que o payload enviado contém somente campos aprovados e não dados sensíveis em texto integral.

### 2.3 Riscos potenciais

Os riscos abaixo são plausíveis no desenho do sistema, mas não foram demonstrados como exploração concluída no repositório atual.

#### 2.3.1 Prompt injection por conteúdo recuperado

- Evidência no código:
  - `local_rag.py` recupera trechos de arquivos Markdown e os incorpora ao contexto da resposta.
  - `multi_agents.py` monta o contexto do agente e o backstory sem uma camada formal de separação entre instruções do sistema, dados do usuário e base recuperada.

- Limitação do controle atual:
  - O filtro lexical de escopo não é um mecanismo de sanitização do conteúdo recuperado.
  - Não há etapa formal de validação de conteúdo de terceiros no código observado.

- Classificação:
  - Risco potencial.

- Por que importa:
  - Trechos recuperados podem conter texto não confiável; se esse conteúdo for tratado como instrução relevante, o modelo pode responder fora do escopo ou seguir regras adversariais.

- Tratamento proposto:
  - Separar claramente instruções do sistema, contexto da aplicação, usuário e conteúdo recuperado.
  - Tratar conteúdo externo como não confiável.
  - Sanitizar e normalizar documentos antes do uso.

- Prioridade:
  - Alta.

- Teste de aceitação:
  - Criar um documento temporário em um diretório isolado, com texto adversarial no padrão do corpus, e verificar que o conteúdo não altera regras da aplicação nem instruções do sistema.

#### 2.3.2 Resposta enganosa e uso indevido em contexto clínico

- Evidência no código:
  - `multi_agents.py` usa `grounded_response()` e `assemble_verified()`, mas isso não elimina interpretação errada do conteúdo nem uso indevido da resposta.
  - O projeto declara não realizar diagnóstico nem prescrição, mas a resposta pode ser interpretada como orientação por quem a receber.

- Limitação do controle atual:
  - O modelo pode gerar texto convincente mesmo quando a base for incompleta ou ambígua.
  - O código não implementa uma camada de validação humana para resposta final em casos de alto risco.

- Classificação:
  - Risco potencial.

- Por que importa:
  - Em saúde, “resposta bem formulada” pode influenciar decisões humanas sem a devida cautela ou evidência bibliográfica adequada.

- Tratamento proposto:
  - Manter restrições explícitas de uso e disclaimer.
  - Exigir base verificável e incerteza declarada quando houver.
  - Revisão humana para cenários sensíveis.

- Prioridade:
  - Alta.

- Teste de aceitação:
  - Usar uma pergunta ambígua em um documento de teste e verificar que a resposta inclui disclaimer claro e não sugere diagnóstico ou prescrição.

#### 2.3.3 Links enganosos e phishing

- Evidência no código:
  - `app.py` usa `st.markdown(..., unsafe_allow_html=False)`.
  - O projeto não possui evidência de HTML/JavaScript executado a partir do conteúdo do modelo na interface atual.

- Limitação do controle atual:
  - O código reduz risco de execução de HTML/JavaScript na renderização, mas não elimina risco de links externos enganadores.
  - O problema aqui é principalmente engenharia social por link, não execução de script na página.

- Classificação:
  - Risco potencial, não execução demonstrada.

- Por que importa:
  - Um usuário pode clicar em link falso ou não confiável mascarado como fonte de informação científica.

- Tratamento proposto:
  - Rotular links externos, limitar e visualizar domínios, e não confiar em links sem validação.

- Prioridade:
  - Média.

- Teste de aceitação:
  - Criar um texto temporário com link suspeito em um ambiente isolado e verificar que ele não é renderizado como HTML bruto e é claramente rotulado como link externo.

#### 2.3.4 Uso de filtros por palavras e prompts de segurança como garantia completa

- Evidência no código:
  - `usage_policy.py` usa expressão regular para permitir/rejeitar domínios e termos.
  - `multi_agents.py` usa instruções explicitamente incorporadas no backstory do agente.

- Limitação do controle atual:
  - Filtros por palavra, regex e prompts de segurança não são garantias completas. Eles funcionam como camadas de redução, mas não substituem validação estrutural, separação de contexto e revisão de saída.
  - Não remover termos de saúde indiscriminadamente, porque isso prejudica o propósito educacional do projeto.

- Classificação:
  - Risco potencial de bypass ou de falsos positivos.

- Por que importa:
  - A aplicação depende de termos críticos de saúde para responder adequadamente; regras excessivamente rígidas podem impedir atendimentos válidos.

- Tratamento proposto:
  - Usar filtros e prompts como complemento, não como única defesa.
  - Avaliar casos duvidosos fora da regra automatizada.

- Prioridade:
  - Média.

- Teste de aceitação:
  - Validar que uma pergunta relevante sobre hipertensão ou diabetes continua sendo aceita, e que um pedido fora do escopo continua sendo rejeitado, sem depender de uma lista fixa de palavras como única crítica.

#### 2.3.5 Ações de escrita e execução de ferramentas perigosas

- Evidência no código observada:
  - Em `multi_agents.py`, as ferramentas definidas são `data_tool`, `ml_tool` e `rag_tool`.
  - `data_tool` chama `query_data(question)`, que é um caminho de consulta; não foi localizado no código um caminho de escrita, exclusão, envio de e-mail ou alteração de sistemas externos.
  - `ml_tool` é uma leitura do modelo local; não foi localizado um caminho de treinamento nem de escrita em disco por essas ferramentas.
  - O fluxo principal usa `requests.post` em `flowise_tokens()` e `langfuse_export.py`, mas não há caminho de execução de comandos perigosos localizado no trecho observado.

- Limitação do controle atual:
  - Não foi localizado no código atual um caminho de escrita ou resposta autonômica fora do contexto de consulta/resposta.
  - O risco existe apenas se novas integrações forem adicionadas ou se a rota do backend for alterada.

- Classificação:
  - Não demonstrado no código atual; risco potencial apenas sob extensão do sistema.

- Por que importa:
  - A arquitetura de agentes pode mudar com o tempo; a separação de funções deve ser mantida para evitar que a aplicação passe a executar ações fora do escopo educacional.

- Tratamento proposto:
  - Manter permissões restritas por ferramenta.
  - Proibir ações de escrita fora do conjunto explícito e aprovado.

- Prioridade:
  - Média.

- Teste de aceitação:
  - Verificar, em ambiente isolado, que nenhuma ferramenta de escrita ou execução de comando é chamada em fluxo padrão do assistente.

## 3) Conformidade e categorias de risco

### 3.1 Confidencialidade interna vs. classificação jurídica

O projeto usa termos como “dados sensíveis”, “traces”, “histórico local”, “conteúdo do usuário” e “dados restritos”, mas isso não equivale a uma classificação jurídica formal. O relatório não afirma conformidade com LGPD, HIPAA, ou qualquer outro regime específico, porque não foi verificada uma análise legal ou um mapeamento regulatório completo.

### 3.2 Objetivo educacional e não diagnóstico

O projeto declara explicitamente que não realiza diagnóstico nem prescrição. Isso reduz o risco de uso clínico indevido do sistema, mas não elimina o risco de resposta enganosa, interpretação indevida ou motivação de ações por parte do usuário. A distinção entre educação em saúde e recomendação individual deve ser mantida em todas as versões do projeto.

## 4) Plano de tratativas proposto

### 4.1 Registro mínimo e mascaramento

- Persistir apenas dados mínimos e mascarados quando o conteúdo do usuário puder incluir informação pessoal ou de saúde.
- Separar histórico, observabilidade e exportação externa.
- Definir política de retenção e expiração para logs, traces e histórico.
- Garantir que “dados mascarados” não sejam interpretados como anonimizados definitivamente; o risco de reidentificação permanece.
- Usar exemplos de dados fictícios em testes para não contaminar o corpus real do projeto.

### 4.2 Limites de integração

- Documentar claramente o que é local, o que é remoto e como cada serviço é acessado.
- Exigir revisão do payload exportado antes de qualquer configuração externa ativa.
- Não considerar Flowise ou Langfuse como equivalentes; cada serviço deve ser avaliado pela sua própria topologia e ameaça.

### 4.3 Arquitetura e validação

- Separar instruções do sistema, contexto da aplicação, conteúdo do usuário e conteúdo recuperado.
- Usar filtros de escopo e prompts de segurança apenas como camadas complementares.
- Validar a saída antes da apresentação e manter regras explícitas de uso do conteúdo.
- Definir escalation humano em cenários sensíveis ou ambíguos.

### 4.4 Testes objetivos

- Usar dados fictícios em documentos temporários e rastros isolados.
- Não escrever em diretórios do corpus real do projeto durante testes de segurança.
- Validar com conteúdo de amostra controlado e repositórios temporários separados.

## 5) Conclusão

O OXICOR apresenta evidências observadas de armazenamento local de histórico e observabilidade, uso de Ollama local como padrão, integração opcional com Flowise e Langfuse, e filtro lexical de escopo. Isso reduz alguns riscos iniciais, mas não elimina riscos de privacidade, uso indevido do conteúdo e resposta enganosa em contexto de saúde.

O relatório foi revisado para manter a distinção entre:

- fatos observados,
- vulnerabilidades demonstradas,
- riscos potenciais,
- medidas de mitigação e testes de aceitação.

Não foram implementados controles nem executados ataques. O relatório usa critérios de evidência e limita a análise ao código observado e às configurações explicitamente identificadas no projeto.
