"""Recuperação lexical TF-IDF sobre resumos locais, sem novos serviços."""
import re
from functools import lru_cache
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import get_setting

@lru_cache(maxsize=1)
def index():
    root = Path(get_setting('OXICOR_RAG_DIR', str(Path(__file__).parent/'rag')))
    chunks = []
    section_id = 0
    for path in sorted(root.glob('*.md')):
        document = path.read_text(encoding='utf-8-sig')
        title = document.splitlines()[0].lstrip('# ')
        for section in re.split(r'\n(?=## )', document):
            lines = section.strip().splitlines()
            if not lines or not lines[0].startswith('## '):
                continue
            heading = lines[0].lstrip('# ')
            if heading == 'Fonte e finalidade':
                continue
            section_id += 1
            for paragraph_index, paragraph in enumerate(
                re.split(r'\n\s*\n', '\n'.join(lines[1:]).strip())
            ):
                if paragraph:
                    chunks.append(dict(
                        source=path.name,
                        title=title,
                        heading=heading,
                        text=paragraph,
                        section_id=section_id,
                        paragraph_index=paragraph_index,
                    ))
    if not chunks:
        raise ValueError('Base RAG local vazia')
    vectorizer = TfidfVectorizer(strip_accents='unicode', ngram_range=(1,2), sublinear_tf=True)
    matrix = vectorizer.fit_transform([c['title']+' '+c['heading']+' '+c['text'] for c in chunks])
    return chunks, vectorizer, matrix

def retrieve(question, top_k=2):
    chunks, vectorizer, matrix = index()
    scores = cosine_similarity(vectorizer.transform([question]), matrix).ravel()
    selected = [
        (int(i), float(scores[i]))
        for i in scores.argsort()[::-1][:top_k]
        if scores[i] >= .07
    ]
    contexts = {}
    for i, score in selected:
        chunk = chunks[i]
        section_id = chunk['section_id']
        context = contexts.setdefault(
            section_id,
            {
                'chunk': chunk,
                'score': score,
                'first_paragraph': chunk['paragraph_index'],
                'last_paragraph': chunk['paragraph_index'],
            },
        )
        context['score'] = max(context['score'], score)
        context['first_paragraph'] = min(
            context['first_paragraph'], chunk['paragraph_index']
        )
        context['last_paragraph'] = max(
            context['last_paragraph'], chunk['paragraph_index']
        )

    results = []
    for section_id, context in contexts.items():
        section_chunks = [
            chunk for chunk in chunks
            if chunk['section_id'] == section_id
            and context['first_paragraph'] - 1
            <= chunk['paragraph_index']
            <= context['last_paragraph'] + 1
        ]
        results.append({
            'source': context['chunk']['source'],
            'title': context['chunk']['title'],
            'heading': context['chunk']['heading'],
            'text': '\n\n'.join(chunk['text'] for chunk in section_chunks),
            'score': round(context['score'], 4),
        })
    return results

def consult_local(question):
    hits = retrieve(question)
    if not hits:
        return 'Não encontrei evidência suficiente na base local OXICOR. Reformule a pergunta ou consulte um profissional.'
    return ('Trechos recuperados dos resumos educacionais locais OXICOR:\n\n'+
            '\n\n'.join(f"**Fonte: {h['source']} · {h['heading']}**\n\n{h['text']}" for h in hits)+
            '\n\nConteúdo educacional. Não substitui avaliação profissional. As referências declaradas nos resumos devem ser conferidas nos documentos originais.')
