"""Recuperação lexical TF-IDF sobre resumos locais, sem novos serviços."""
import os
import re
from functools import lru_cache
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@lru_cache(maxsize=1)
def index():
    root = Path(os.getenv('OXICOR_RAG_DIR', str(Path(__file__).parent/'rag')))
    chunks = []
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
            for paragraph in re.split(r'\n\s*\n', '\n'.join(lines[1:]).strip()):
                if paragraph:
                    chunks.append(dict(source=path.name, title=title, heading=heading, text=paragraph))
    if not chunks:
        raise ValueError('Base RAG local vazia')
    vectorizer = TfidfVectorizer(strip_accents='unicode', ngram_range=(1,2), sublinear_tf=True)
    matrix = vectorizer.fit_transform([c['title']+' '+c['heading']+' '+c['text'] for c in chunks])
    return chunks, vectorizer, matrix

def retrieve(question, top_k=2):
    chunks, vectorizer, matrix = index()
    scores = cosine_similarity(vectorizer.transform([question]), matrix).ravel()
    return [dict(chunks[i], score=round(float(scores[i]),4)) for i in scores.argsort()[::-1][:top_k] if scores[i]>=.07]

def consult_local(question):
    hits = retrieve(question)
    if not hits:
        return 'Não encontrei evidência suficiente na base local OXICOR. Reformule a pergunta ou consulte um profissional.'
    return ('Trechos recuperados dos resumos educacionais locais OXICOR:\n\n'+
            '\n\n'.join(f"**Fonte: {h['source']} · {h['heading']}**\n\n{h['text']}" for h in hits)+
            '\n\nConteúdo educacional. Não substitui avaliação profissional. As referências declaradas nos resumos devem ser conferidas nos documentos originais.')
