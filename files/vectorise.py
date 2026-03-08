import os
import openai
from django.conf import settings
from ai.constants import OPENAI_API_KEY
from files.models.files import File
from files.models.file_chunk import FileChunk


def _get_file_path(file: File) -> str:
    dest_dir = os.path.join(settings.STATIC_ROOT, "uploads", "files")
    return os.path.join(dest_dir, f'{file.id}{file.extension}')


# --- Text extractors per file type ---

def extract_text_from_txt(path):
    with open(path, 'r', errors='ignore') as f:
        return f.read()


def extract_text_from_pdf(path):
    import pypdf
    text = []
    with open(path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text() or '')
    return '\n'.join(text)


def extract_text_from_docx(path):
    import docx
    doc = docx.Document(path)
    return '\n'.join(p.text for p in doc.paragraphs)


def extract_text_from_csv(path):
    with open(path, 'r', errors='ignore') as f:
        return f.read()


def extract_text_from_image(path):
    import base64
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    mime = f'image/{ext}' if ext != 'jpg' else 'image/jpeg'
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
                {'type': 'text', 'text': 'Describe everything in this image in detail.'},
            ]
        }]
    )
    return response.choices[0].message.content


EXTRACTORS = {
    '.txt':  extract_text_from_txt,
    '.md':   extract_text_from_txt,
    '.json': extract_text_from_txt,
    '.csv':  extract_text_from_csv,
    '.pdf':  extract_text_from_pdf,
    '.docx': extract_text_from_docx,
    '.doc':  extract_text_from_docx,
    '.png':  extract_text_from_image,
    '.jpg':  extract_text_from_image,
    '.jpeg': extract_text_from_image,
    '.webp': extract_text_from_image,
}


# --- Chunking ---
def chunk_text(text, max_words=500, overlap=50):
    import re
    chunks = []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    for paragraph in paragraphs:
        words = paragraph.split()

        if len(words) <= max_words:
            chunks.append(paragraph)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            current_chunk = []
            current_len = 0

            for sentence in sentences:
                sentence_words = sentence.split()

                if current_len + len(sentence_words) <= max_words:
                    current_chunk.append(sentence)
                    current_len += len(sentence_words)
                else:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    if len(sentence_words) > max_words:
                        start = 0
                        while start < len(sentence_words):
                            chunks.append(' '.join(sentence_words[start:start + max_words]))
                            start += max_words - overlap
                    else:
                        current_chunk = [sentence]
                        current_len = len(sentence_words)

            if current_chunk:
                chunks.append(' '.join(current_chunk))

    return chunks


# --- Embedding ---
def get_embeddings(texts: list[str]) -> list[list[float]]:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    embeddings = []
    batch_size = 100  # safe batch size well within token limits

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model='text-embedding-ada-002', input=batch)
        embeddings.extend([item.embedding for item in response.data])

    return embeddings

# --- Main vectorisation entry point ---
def vectorise_file(file: File):
    ext = file.extension.lower()
    extractor = EXTRACTORS.get(ext)
    if not extractor:
        raise ValueError(f'Unsupported file type: {ext}')

    path = _get_file_path(file)
    text = extractor(path)

    if not text or not text.strip():
        raise ValueError(f'No text could be extracted from {file.file_name}')

    chunks = chunk_text(text)
    embeddings = get_embeddings(chunks)

    FileChunk.objects.bulk_create([
        FileChunk(file=file, chunk_index=i, content=chunk, embedding=embedding)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ])