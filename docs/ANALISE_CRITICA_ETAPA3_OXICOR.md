# OXICOR — Análise crítica da etapa 3

Autor: Alexandre Augusto Chizzali
Projeto acadêmico PUCPR — AI Factory Building Intelligent Systems
Data: 13 de novembro de 2026

## Parte A — Revisitando o desafio

### Acesso e proposta original

Site: https://oxicor-aug1989.streamlit.app/
Repositório: https://github.com/aug1989/oxicor-assistente-cardiometabolico
Branch da publicação: `etapa3-deploy`. Commit da inclusão dos relatórios de demonstração: `394269251dab97e0a4b7c5fa44f7ae050ff47781`.

A grande ideia definida na etapa 1 foi aplicar tecnologia e inteligência artificial à prevenção e à educação em saúde cardiometabólica. A pergunta essencial foi: “Como a inteligência artificial pode transformar dados de saúde e conhecimento científico em informações acessíveis que ajudem as pessoas a compreender melhor seus riscos cardiometabólicos?”

O desafio consistiu em desenvolver um assistente educacional inteligente para a OXICOR, integrando dados estruturados de triagem cardiometabólica a uma base científica sobre hipertensão, obesidade e diabetes tipo 2, com consultas em linguagem natural e respostas fundamentadas por recuperação de informações, ou RAG. O propósito registrado foi “Levar saúde ao longo do caminho”.

A justificativa pessoal registrada na primeira etapa relaciona a atuação do autor na saúde e na área cardiovascular ao interesse por prevenção, fatores de risco e aplicações de Saúde 4.0. O projeto procura aproximar esse conhecimento profissional de uma interface acessível, sem substituir a avaliação de profissionais de saúde.

### Em que medida o sistema resolve o desafio?

O sistema atende ao desafio como protótipo educacional funcional. A versão publicada reúne chat, recuperação de conteúdo, consultas estruturadas, relatórios e demonstração de um modelo de aprendizado de máquina. O usuário consegue acessar essas funções pela internet, sem instalar o ambiente de desenvolvimento no próprio computador.

Na demonstração de RAG, a pergunta sobre preparo para medir a pressão arterial retornou trechos do resumo de hipertensão, incluindo repouso e condições de aferição, com identificação da fonte. Isso demonstra a ligação entre uma pergunta e o conteúdo disponível na base. Entretanto, a resposta observada apresenta trechos extensos: preservar a fonte ajuda na rastreabilidade, mas ainda há espaço para melhorar a clareza e a síntese para pessoas sem formação técnica.

A consulta estruturada retornou sete participantes da base fictícia. Os relatórios publicados exibiram sete participantes e nove triagens, além das categorias e alertas já registrados. Uma consulta individual recuperou a última triagem do identificador fictício `PRINT_CODE_001`. O sistema também distinguiu um participante cadastrado sem triagem, apresentando uma mensagem de ausência de registros. Esses exemplos mostram que a interface oferece acesso a dados existentes sem precisar gerar SQL livre com o modelo de linguagem.

Na etapa de aprendizado de máquina, um perfil explicitamente fictício foi encaminhado à rota ML. A aplicação retornou classe 0, escore de 1,4% para a classe positiva e limiar de classificação de 13%. O resultado demonstrou a utilização do modelo salvo na aplicação publicada. Não demonstra, porém, que o sistema estima corretamente o risco clínico de uma pessoa: o alvo é a classificação de diabetes ou pré-diabetes no dataset utilizado, e não uma previsão validada de doença futura.

O desafio foi, portanto, atendido de forma parcial e delimitada. Foi construída uma integração funcional entre conhecimento textual, dados estruturados e classificação estatística. Ainda não foi demonstrado que usuários compreendem melhor sua saúde após utilizar o sistema, nem houve validação clínica, estudo prospectivo ou avaliação de impacto sobre prevenção. Os dados de triagem publicados são fictícios, e o corpus educacional é pequeno. Esses limites impedem apresentar o protótipo como solução clínica pronta.

### Evolução até a publicação

A primeira etapa dependia de serviços locais, incluindo Flowise, Ollama e PostgreSQL. A versão de demonstração publicada utiliza Streamlit Community Cloud, OpenRouter com o modelo `google/gemini-2.5-flash-lite`, recuperação local dos resumos e DuckDB para os CSVs fictícios. A integração PostgreSQL permanece opcional.

Essa adaptação reduziu a dependência do notebook para apresentar o projeto. A hospedagem da interface foi separada da execução do modelo de linguagem, que depende de uma API e de créditos disponíveis. A escolha do Streamlit preservou a interface existente; a plataforma de exemplo utilizada pelo professor não foi tratada como requisito obrigatório da entrega.

Durante a publicação ocorreram falhas de permissão relacionadas a caminhos concebidos para Docker. A correção utilizou diretório temporário gravável para arquivos de execução e caminhos relativos ao código para localizar os dados. Posteriormente, a página Relatórios foi adaptada para utilizar a base fictícia local quando PostgreSQL não estivesse configurado. A interface identifica essa origem e não troca silenciosamente uma conexão PostgreSQL com erro pelos dados locais.

## Parte B — Análise técnica

### O que funciona bem e por quê

**Separação das funções.** O encaminhamento distingue conteúdo educacional, consulta de dados e classificação ML. Essa divisão permite restringir as operações e observar qual componente produziu o resultado. Nos exemplos públicos, foram exercitadas as três rotas e a página Relatórios.

**Rastreabilidade do RAG.** As respostas apresentam fontes e trechos recuperados. Isso facilita conferir a origem da informação. A falha histórica do caso G11 mostrou que uma resposta pode ser fiel ao contexto recuperado e ainda assim omitir parte da pergunta. A correção de recuperação foi seguida por nova avaliação dos seis casos RAG G08–G13, preservando os critérios e os registros anteriores.

**Consulta controlada de dados.** Os relatórios utilizam consultas restritas e parâmetros para os identificadores. Não recalculam classificações clínicas. A interface distingue contagens de participantes e de triagens, evitando interpretar vários registros de uma pessoa como várias pessoas.

**Modelo disponível na hospedagem.** A demonstração ML utilizou o artefato salvo, sem necessidade de novo treinamento. A resposta apresenta classe, escore, limiar e limitação educacional. Na ausência das variáveis necessárias, o sistema solicita os campos em vez de inventar uma classificação.

**Controles de segurança e privacidade.** Foram implementados mascaramento de padrões comuns de identificadores, limites de uso, histórico por sessão, desativação padrão de observabilidade persistente e ativação explícita de Langfuse. As credenciais ficam fora do código versionado. Esses controles reduzem exposição, mas não garantem anonimização ou conformidade jurídica.

### Problemas encontrados e limitações

| Aspecto | Limitação e consequência |
|---|---|
| Recuperação textual | Corpus pequeno e busca local podem deixar de recuperar trechos relevantes ou lidar mal com formulações diferentes. A melhora de G11 não prova cobertura geral. |
| Qualidade das respostas | Trechos extensos e repetição das respostas dos agentes podem prejudicar a leitura. Preservação da evidência não equivale a boa comunicação. |
| ML | O modelo não foi validado clinicamente na população atendida pela OXICOR. O escore não deve ser apresentado como probabilidade clínica individual calibrada. |
| Dados de demonstração | Sete participantes e nove triagens fictícias demonstram operações, mas não permitem conclusões sobre prevalência ou desempenho em uma população real. |
| Relatórios | Alertas e categorias são valores previamente registrados. O filtro operacional de PA não estabelece diagnóstico. As perguntas em linguagem natural são limitadas às intenções implementadas. |
| Persistência | Histórico de conversa fica na sessão; arquivos de execução na hospedagem são transitórios. Reinicializações podem perder estado e reiniciar limites locais. |
| Acesso | Não há autenticação de usuários finais para uso clínico. Páginas administrativas ocultas não equivalem a controle de autorização. |
| Provedor de IA | Chat depende de conectividade, disponibilidade, saldo e limites do OpenRouter. Uma solicitação pode envolver várias chamadas. Não foi medido um custo médio representativo por atendimento. |
| Segurança | Filtros lexicais e mascaramento por padrões não cobrem todos os dados identificáveis ou ataques. Mocks não comprovam a segurança de integrações reais. |
| Operação | A demonstração manual não substitui testes de carga, monitoramento contínuo, validação real entre sessões e plano de recuperação. |

### Evidências e alcance da validação

É necessário distinguir resultados de diferentes momentos e ambientes:

- A seleção focalizada de segurança apresentou 26 testes aprovados, sem falhas ou ignorados, em 10,82 segundos na execução registrada. Uma execução manual anterior da mesma seleção havia apresentado 3,41 segundos.
- A regressão da alteração de Relatórios foi informada como 68 testes aprovados, mais dois subtestes, em container temporário sem rede. Essa evidência não equivale a uma conexão real com PostgreSQL.
- Os resultados DeepEval preservam execuções anteriores e posteriores à correção do RAG. Os seis casos RAG passaram após a correção; isso não foi uma nova execução conjunta dos quinze casos e não valida automaticamente o modelo OpenRouter da publicação.
- Na aplicação pública, foram apresentados resultados de RAG, consulta de sete participantes, classificação de um perfil fictício e Relatórios. As capturas de Relatórios registram os indicadores, a consulta individual e as distribuições.
- Não foram demonstrados, nesta validação, carga concorrente, isolamento entre duas sessões reais, treinamento completo na nuvem ou uma avaliação completa do golden dataset com o provedor atual.

### Arquitetura da demonstração publicada

```text
Navegador → Streamlit Community Cloud
              ├── Chat → encaminhamento/orquestração → OpenRouter
              │          ├── RAG → resumos Markdown locais
              │          ├── Dados → DuckDB / CSVs fictícios
              │          └── ML → modelo salvo
              ├── Relatórios → DuckDB / CSVs fictícios
              │                └── PostgreSQL opcional
              └── Histórico → sessão temporária do usuário
```

Flowise e Langfuse são integrações opcionais; não são necessários para reproduzir os exemplos públicos aqui descritos. O modelo de linguagem, o modelo de classificação ML e os dados fictícios cumprem papéis diferentes e não devem ser confundidos.

## Parte C — Visão de futuro

| Proposta | O que mudaria | Tecnologia ou método | Impacto esperado e verificação |
|---|---|---|---|
| Ampliar e avaliar a recuperação | Expandir o corpus revisado, melhorar segmentação e testar sinônimos e perguntas incompletas. | Busca híbrida lexical/semântica, embeddings e reranking, comparados com o recuperador atual; DeepEval e revisão humana. | Menos omissões de trechos relevantes. Medir recuperação e completude em conjunto de avaliação ampliado sem alterar os critérios para esconder falhas. |
| Validar o modelo ML | Avaliar discriminação, calibração, falsos positivos e diferenças entre subgrupos em dados adequadamente autorizados. | scikit-learn, curvas de calibração, métricas por subgrupo e validação externa com separação rigorosa dos conjuntos. | Entender os limites de generalização e evitar interpretação indevida dos escores. Uso clínico exigiria avaliação adicional específica. |
| Adicionar acesso e persistência controlados | Criar contas, autorização por perfil e separação de dados por usuário, com retenção justificada. | Provedor de identidade OIDC, PostgreSQL e controles de acesso no servidor; testes de autorização e isolamento. | Viabilizar continuidade de uso com menor exposição entre usuários. Confirmar que uma conta não acessa registros de outra. |
| Melhorar operação e custos | Monitorar erros, disponibilidade, latência e consumo com registros mínimos. | Integração contínua, testes de fumaça, métricas agregadas e limites no provedor, com observabilidade explicitamente configurada. | Detectar regressões e indisponibilidade antes da apresentação ou uso. Acompanhar custo e latência por cenário sem registrar desnecessariamente conteúdo sensível. |
| Tornar a interface mais acessível | Reduzir repetição dos agentes e apresentar síntese clara com fontes expansíveis. | Componentes Streamlit, revisão de linguagem e testes de usabilidade com público representativo. | Melhor compreensão e navegação. Avaliar execução de tarefas e entendimento das limitações, preservando fidelidade às fontes. |

## Reflexão sobre o processo

O que mais me surpreendeu foi a facilidade de utilizar ferramentas de apoio à construção e a rapidez com que foi possível desenvolver e ajustar o projeto. Ao mesmo tempo, a experiência evidenciou a importância da infraestrutura: armazenamento, configuração de serviços, permissões e hospedagem influenciam diretamente o funcionamento da aplicação. A facilidade de gerar código não elimina a necessidade de testar, compreender os resultados e documentar as limitações.

## Referências e evidências do projeto

- Proposta original: docs/ETAPA1.md.
- Metodologia e avaliação do modelo: docs/RELATORIO_ETAPA2.md.
- Avaliações de linguagem e recuperação: evaluation/deepeval_evidence/.
- Segurança: RELATORIO_SEGURANCA_LLM.md e evaluation/security_evidence/.
- Publicação e reprodução: README.md e docs/DEPLOY.md.
- Capturas da aplicação: EVIDENCIAS_RELATORIOS_OXICOR.pdf, anexo desta entrega. As capturas demonstram os cenários apresentados, sem equivaler a validação clínica ou auditoria completa.
