import openai
from pgvector.django import L2Distance
from ai.constants import OPENAI_API_KEY
from files.models.file_chunk import FileChunk
from files.models.conversation import Conversation
from files.models.file_conversation import FileConversation


def embed_question(question: str) -> list[float]:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        model='text-embedding-ada-002',
        input=question
    )
    return response.data[0].embedding


def get_relevant_chunks(conv_id: str, question_embedding: list[float], top_k: int = 5):
    """
    Find the top_k most similar chunks across all files in this conversation.
    """
    return (
        FileChunk.objects
        .filter(file__file_conversation__conv_id=conv_id)
        .annotate(distance=L2Distance('embedding', question_embedding))
        .order_by('distance')
        .select_related('file')[:top_k]
    )


def build_context(chunks) -> tuple[str, list[dict]]:
    """
    Build the context string to pass to GPT and the references list to return to the UI.
    """
    context_parts = []
    references = []

    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[{i+1}] File: {chunk.file.file_name} | Chunk {chunk.chunk_index}\n{chunk.content}"
        )
        references.append({
            'file': chunk.file.file_name,
            'chunk': chunk.chunk_index,
        })

    return '\n\n'.join(context_parts), references


def ask_gpt(question: str, context: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {
                'role': 'system',
                'content': (
                    "You are a document analysis assistant. "
                    "Answer the user's question strictly based on the provided document context. "
                    "If the answer is not in the context, say so clearly. "
                    "When referencing information, mention the file name it came from."
                )
            },
            {
                'role': 'user',
                'content': f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )
    return response.choices[0].message.content


def handle_query(conv_id: str, question: str) -> dict:
    """
    Main entry point:
    1. Embed the question
    2. Find similar chunks
    3. Ask GPT
    4. Save to Conversation
    5. Return answer + references
    """
    file_conversation = FileConversation.objects.get(conv_id=conv_id)

    # 1. Embed question
    question_embedding = embed_question(question)

    # 2. Similarity search
    chunks = get_relevant_chunks(conv_id, question_embedding)
    if not chunks:
        return {'answer': 'No relevant content found in the uploaded files.', 'references': []}

    # 3. Build context + references
    context, references = build_context(chunks)

    # 4. Ask GPT
    answer = ask_gpt(question, context)

    # 5. Persist both turns
    Conversation.objects.create(
        file_conversation=file_conversation,
        role=Conversation.Role.USER,
        content=question,
        references=[],
    )
    Conversation.objects.create(
        file_conversation=file_conversation,
        role=Conversation.Role.ASSISTANT,
        content=answer,
        references=references,
    )

    return {'answer': answer, 'references': references}