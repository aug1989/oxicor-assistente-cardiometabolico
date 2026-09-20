# Streamlit: conceitos no OXICOR

## Streaming
Streaming significa receber e mostrar partes da resposta enquanto o servidor as envia. No app, `flowise_tokens()` usa o mesmo endpoint de prediction com `streaming=True` no JSON e `stream=True` no requests. O primeiro solicita streaming ao Flowise; o segundo evita carregar a resposta inteira antes da leitura.

`sse_events()` monta eventos SSE recebidos pela rede. Somente eventos `token` alimentam `st.write_stream(flowise_tokens(...))`, que atualiza a interface. Eventos de thinking não são renderizados. Não há espera artificial nem divisão de resposta pronta para simular digitação. Se o Flowise devolver JSON integral, o app mostra o texto inteiro e informa essa condição. O início do texto ainda pode demorar durante retrieval/inferência.

## Session state
`st.session_state` mantém dados entre reruns: cada clique ou mensagem pode reexecutar o script. Um dicionário Python comum recriado no início não conservaria esses dados.

- `st.session_state.chats`: dicionário de conversas indexado por UUID.
- `st.session_state.active_chat_id`: conversa selecionada.
- `chats[id]['messages']`: mensagens dessa conversa, incluindo resposta parcial/erro se necessário.
- `chats[id]['session_id']`: identificador enviado ao Flowise em chatId e overrideConfig.sessionId.
- `chats[id]['title']`: primeira pergunta abreviada ou título inicial.

O session_state continua temporário: refresh recria a conexão WebSocket. Agora load_history() restaura os chats do SQLite dedicado, independentemente da memória do Flowise.

## Callback
Callback é uma função executada quando um evento da interface ocorre. O Streamlit executa o callback antes de reexecutar o restante do script.

```python
st.button('Nova conversa', on_click=new_chat)
st.button(titulo, on_click=select_chat, args=(cid,))
```

`new_chat()` cria um UUID, uma lista vazia de mensagens e seleciona a conversa, preservando as anteriores. `select_chat(cid)` muda apenas a conversa ativa. O gerador de tokens não é um callback de botão: ele fornece dados progressivamente ao consumidor `st.write_stream`.

## Mensagens versus múltiplos chats
Histórico de mensagens é a sequência usuário/assistente de uma conversa. Múltiplos chats são várias sequências independentes, cada qual com seu identificador. Selecionar um chat restaura sua sequência e seu sessionId; iniciar outro não apaga o anterior.

## Limites
A memória do lado Flowise continua dependendo do fluxo existente. Respostas interrompidas ficam identificadas como incompletas. Não há reenvio automático de perguntas após erro. Metadados SSE não são despejados na interface, e a chave continua apenas no ambiente do servidor.

## Referências
- https://docs.flowiseai.com/using-flowise/streaming
- https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- https://docs.streamlit.io/develop/api-reference/write-magic/st.write_stream

## Validação anterior, antes da persistência (08/09/2026)

- Navegador em http://localhost:8501: abriu normalmente.
- Envio de `oi`: resposta recebida; foi observado texto parcial antes da conclusão, confirmando atualização progressiva real.
- Nova conversa: abriu vazia e manteve a primeira na lista.
- Envio de `Olá, responda brevemente.`: resposta recebida na segunda conversa.
- Seleção da conversa `oi`: mensagens anteriores restauradas integralmente.
- Reload da página: histórico local perdido; apareceu somente `Conversa 1` vazia, como esperado para uma nova sessão WebSocket.
- Testes controlados: SSE Flowise e SSE padrão, UTF-8, heartbeat, eventos de thinking ignorados, callbacks, sessões independentes, restauração de histórico, preservação de resposta parcial em erro e JSON integral identificado passaram.
- `.env`, Dockerfile e compose.yaml foram comparados por hash e permaneceram idênticos. Somente o container Streamlit foi recriado para carregar app.py.
- O Flowise respondeu às saudações com texto científico. O conteúdo e o comportamento do AgentFlow não foram alterados por esta implementação.


## Persistência local: complemento ao session_state

Session state = estado temporário da interface entre reruns. Persistência = armazenamento durável fora da sessão. Usamos ambos: a interface trabalha com `chats` e `active_chat_id` em session_state, enquanto `save_chat()` e `save_active()` gravam SQLite e `load_history()` restaura os dados ao abrir/recarregar.

O banco `/app/data/history.sqlite3` fica no volume `streamlit-flowise-chat_chat_history`. A tabela `chats` guarda ID, título, sessionId, data de criação e mensagens JSON ordenadas (role, conteúdo, timestamp e estado da resposta). `settings` guarda a conversa ativa. As gravações usam transações SQLite e parâmetros SQL; somente os campos permitidos são serializados, sem chave/API/env.

`new_chat()` e `select_chat()` continuam callbacks on_click, agora também persistindo a seleção. `flowise_tokens()` e `st.write_stream()` continuam recebendo/exibindo SSE real. O app salva a pergunta antes da requisição e a resposta ao terminar ou falhar; refresh durante a geração pode perder tokens ainda não confirmados, mas mantém a pergunta e identifica a resposta pendente.

O volume é independente da imagem e sobrevive a reinício e rebuild. Remover o volume explicitamente apaga o banco. Este é um histórico local compartilhado, sem isolamento de usuários.

## Validação da persistência

Dois chats identificados como testes locais foram criados com respostas SSE controladas, sem requisições ao Flowise. O navegador confirmou ambos após refresh e após restart somente do container Streamlit. Abrir o primeiro chat restaurou suas mensagens. A conversa ativa também foi restaurada. SQLite integrity_check retornou ok e a página HTTP 200. O streaming foi validado com tokens SSE controlados; não foram enviadas perguntas médicas. Os dois chats de teste permanecem visíveis para conferência.
