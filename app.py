from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import datetime
from docx import Document
import os
from dotenv import load_dotenv
import numpy as np
import faiss
import time
import backoff
import glob

app = Flask(__name__)
load_dotenv() # Load environment variables from .env file

# Initialize NetMind API
client = OpenAI(
    base_url="https://api.netmind.ai/inference-api/openai/v1",
    api_key=os.getenv("OPEN_API_KEY")
)

# Load all .docx files in the directory
docs = glob.glob("*.docx")

faq_chunks = []
for doc in docs:
    doc_file = Document(doc)
    faq_chunks.extend([para.text.strip() for para in doc_file.paragraphs if para.text.strip()])

# Initialize NetMind API
client = OpenAI(
    base_url="https://api.netmind.ai/inference-api/openai/v1",
    api_key=os.getenv("OPEN_API_KEY")
)

# Add backoff decorator to handle rate limiting
@backoff.on_exception(backoff.expo,
                     Exception,  # Catch all exceptions since we don't know exact NetMind error types
                     max_tries=5)
def get_embedding(text):
    try:
        response = client.embeddings.create(
            model="BAAI/bge-m3",  # Using NetMind model
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"API error: {e}")
        time.sleep(5)  # Wait before retry
        raise  # Let backoff handle the retry

# ========== AfroZoomer Assistant Class ==========
class AfroZoomerAssistant:
    def __init__(self):
        self.name = "AfroZoomer"
        self.conversation_history = []

        # Use a persistent cache for embeddings to avoid regenerating them
        self.embedding_cache_file = "embedding_cache.npy"
        self.chunks_cache_file = "chunks_cache.txt"

        # Load or create index
        try:
            self.initialize_from_cache()
        except (FileNotFoundError, Exception) as e:
            print(f"Cache not found or error: {e}. Building new index...")
            self.initialize_new_index()

    def initialize_from_cache(self):
        """Load pre-computed embeddings and chunks from cache"""
        # Load embeddings and rebuild index
        saved_embeddings = np.load(self.embedding_cache_file)
        self.embedding_dim = saved_embeddings.shape[1]
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(saved_embeddings.astype("float32"))

        # Load cached chunks
        with open(self.chunks_cache_file, 'r', encoding='utf-8') as f:
            self.faq_chunks = [line.strip() for line in f.readlines()]

        print(f"Loaded {len(self.faq_chunks)} FAQ chunks from cache")

    def initialize_new_index(self):
        """Build a new index by computing embeddings for all chunks"""
        self.faq_chunks = faq_chunks  # Use the globally loaded faq_chunks

        # Get dimension from sample
        sample_emb = get_embedding("sample")
        self.embedding_dim = len(sample_emb)
        self.index = faiss.IndexFlatL2(self.embedding_dim)

        # Process chunks in small batches to avoid rate limits
        all_embeddings = []
        batch_size = 5  # Adjust based on API limits

        for i in range(0, len(self.faq_chunks), batch_size):
            batch = self.faq_chunks[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(self.faq_chunks) + batch_size - 1)//batch_size}")

            for chunk in batch:
                try:
                    emb = get_embedding(chunk)
                    all_embeddings.append(emb)
                    # Don't add to index yet - we'll do it once at the end
                except Exception as e:
                    print(f"Error embedding chunk: {e}")
                    # Use a zero vector as fallback
                    all_embeddings.append([0] * self.embedding_dim)

            # Sleep between batches to avoid hitting rate limits
            time.sleep(5)

        # Convert to numpy array and add to index
        embeddings_np = np.array(all_embeddings).astype("float32")
        self.index.add(embeddings_np)

        # Save to cache
        try:
            np.save(self.embedding_cache_file, embeddings_np)
            with open(self.chunks_cache_file, 'w', encoding='utf-8') as f:
                for chunk in self.faq_chunks:
                    f.write(chunk + '\n')
            print(f"Saved {len(self.faq_chunks)} FAQ chunks to cache")
        except Exception as e:
            print(f"Failed to save cache: {e}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_contextual_faq(self, user_prompt):
        try:
            emb = get_embedding(user_prompt)
            emb_np = np.array([emb]).astype("float32")
            _, I = self.index.search(emb_np, k=3)  # top 3 FAQ matches
            relevant_faqs = [self.faq_chunks[i] for i in I[0] if i < len(self.faq_chunks)]
            return "\n".join(relevant_faqs)
        except Exception as e:
            print(f"Error getting contextual FAQ: {e}")
            # Fallback to returning first few FAQs
            return "\n".join(self.faq_chunks[:3])

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_response(self, user_input):
        try:
            context = self.get_contextual_faq(user_input)
            if not context:
                return "I'm not sure about that. Can you provide more context?"

            system_instruction = "You are AfroZoomer, an assistant who answers questions about Zoomer Africa. " \
                                 "Based on the provided context, answer the user's question accurately. " \
                                 "If the context doesn't explicitly mention the founder, state that the information is not available in the current documents."

            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_input}"}
            ]

            response = client.chat.completions.create(
                model="Qwen/Qwen3-8B",
                messages=messages,
                max_tokens=4096,
                temperature=0.6,
                top_p=0.9,
            )

            answer = response.choices[0].message.content.strip()
            if "I'm not sure" in answer or "I don't know" in answer or "not available in the current documents" in answer.lower():
                return "I'm not sure about that based on the information I have. Can you provide more context?"

            return answer

        except Exception as e:
            print(f"Error getting response: {e}")
            return "I'm sorry, I encountered an error. Please try again later."

# Initialize assistant on first request instead of at startup
assistant = None

def get_assistant():
    global assistant
    if assistant is None:
        assistant = AfroZoomerAssistant()
    return assistant

# ========== Flask Routes ==========
@app.route('/')
def home():
    return render_template("zoomer.html")

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    assistant = get_assistant()  # Get or initialize assistant
    response = assistant.get_response(user_input)
    return jsonify({'response': response})

if __name__ == "__main__":
    # Listen on the right port for Render
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
