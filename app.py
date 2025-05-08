from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import datetime
from docx import Document
import os
from dotenv import load_dotenv
import numpy as np
import faiss
import time
import backoff  # You'll need to install this: pip install backoff

app = Flask(__name__)

load_dotenv()  # Load environment variables from .env file

# Initialize NetMind API
client = OpenAI(
    base_url="https://api.netmind.ai/inference-api/openai/v1",
    api_key=os.getenv("OPEN_API_KEY")
)

# ===== Load Zoomer Africa Data from DOCX Files =====
def load_data_from_docx(filepath):
    """Loads text content from a .docx file."""
    try:
        doc = Document(filepath)
        chunks = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        print(f"Loaded {len(chunks)} paragraphs from {filepath}")
        return chunks
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return []
    except Exception as e:
        print(f"Error reading .docx file: {e}")
        return []

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
        self.embedding_dim = None
        self.index = None
        self.data_chunks = self._load_all_data()  # Load data from both files

        # Use a persistent cache for embeddings to avoid regenerating them
        self.embedding_cache_file = "all_data_embedding_cache.npy"
        self.chunks_cache_file = "all_data_chunks_cache.txt"

        # Load or create index
        try:
            self.initialize_from_cache()
        except (FileNotFoundError, Exception) as e:
            print(f"Cache not found or error: {e}. Building new index...")
            self.initialize_new_index()

    def _load_all_data(self):
        """Loads data from all specified .docx files."""
        all_chunks = []
        all_chunks.extend(load_data_from_docx("zoomer_faqs.docx"))
        all_chunks.extend(load_data_from_docx("zoomer.docx"))  # Assuming the other file is named "zoomer.docx"
        return [chunk for chunk in all_chunks if chunk] # Remove any empty strings

    def initialize_from_cache(self):
        """Load pre-computed embeddings and chunks from cache"""
        if not self.data_chunks:
            raise FileNotFoundError("No data chunks loaded. Cannot initialize from cache.")

        try:
            saved_embeddings = np.load(self.embedding_cache_file)
            self.embedding_dim = saved_embeddings.shape[1]
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index.add(saved_embeddings.astype("float32"))

            with open(self.chunks_cache_file, 'r', encoding='utf-8') as f:
                cached_chunks = [line.strip() for line in f.readlines()]
                if len(cached_chunks) == len(self.data_chunks) and all(c1 == c2 for c1, c2 in zip(cached_chunks, self.data_chunks)):
                    print(f"Loaded {len(self.data_chunks)} data chunks and embeddings from cache")
                else:
                    print("Cached chunks do not match current data. Rebuilding index.")
                    raise FileNotFoundError  # Force rebuild
        except FileNotFoundError:
            raise
        except Exception as e:
            print(f"Error loading cache: {e}. Rebuilding index.")
            raise

    def initialize_new_index(self):
        """Build a new index by computing embeddings for all data chunks"""
        if not self.data_chunks:
            print("No data chunks to index.")
            return

        print(f"Building new FAISS index for {len(self.data_chunks)} chunks...")

        # Get dimension from sample if not already known
        if self.embedding_dim is None and self.data_chunks:
            try:
                sample_emb = get_embedding(self.data_chunks[0])
                self.embedding_dim = len(sample_emb)
                self.index = faiss.IndexFlatL2(self.embedding_dim)
            except Exception as e:
                print(f"Error getting initial embedding: {e}")
                return

        all_embeddings = []
        batch_size = 5  # Adjust as needed based on rate limits and memory
        num_chunks = len(self.data_chunks)

        for i in range(0, num_chunks, batch_size):
            batch = self.data_chunks[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(num_chunks + batch_size - 1)//batch_size}")
            batch_embeddings = []
            for chunk in batch:
                try:
                    emb = get_embedding(chunk)
                    batch_embeddings.append(emb)
                except Exception as e:
                    print(f"Error embedding chunk: {e}")
                    batch_embeddings.append(np.zeros(self.embedding_dim).tolist() if self.embedding_dim else []) # Fallback

            if batch_embeddings:
                all_embeddings.extend(batch_embeddings)
                embeddings_np = np.array(batch_embeddings).astype("float32")
                if self.index is not None:
                    self.index.add(embeddings_np)
                elif not all_embeddings: # Handle case where initial embedding failed
                    print("Failed to build index due to embedding errors.")
                    return
            time.sleep(5) # Be mindful of rate limits

        if all_embeddings and self.index is None:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index.add(np.array(all_embeddings).astype("float32"))

        # Save to cache
        if all_embeddings and self.embedding_dim is not None and self.index is not None:
            try:
                embeddings_np = np.array(all_embeddings).astype("float32")
                np.save(self.embedding_cache_file, embeddings_np)
                with open(self.chunks_cache_file, 'w', encoding='utf-8') as f:
                    for chunk in self.data_chunks:
                        f.write(chunk + '\n')
                print(f"Saved {len(self.data_chunks)} data chunks and embeddings to cache")
            except Exception as e:
                print(f"Failed to save cache: {e}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_contextual_data(self, user_prompt):
        if self.index is None or not self.data_chunks:
            return "No data available."
        try:
            emb = get_embedding(user_prompt)
            emb_np = np.array([emb]).astype("float32")
            D, I = self.index.search(emb_np, k=3)  # top 3 data matches
            relevant_data = [self.data_chunks[i] for i in I[0] if i < len(self.data_chunks)]
            return "\n".join(relevant_data)
        except Exception as e:
            print(f"Error getting contextual data: {e}")
            return "\n".join(self.data_chunks[:3]) # Fallback

    def get_response(self, user_input):
        if not self.data_chunks:
            return "Sorry, the Zoomer Africa data is currently unavailable."
        try:
            context = self.get_contextual_data(user_input)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are AfroZoomer, an assistant for Zoomer Africa. "
                        f"Use the following information to answer the user's question. "
                        f"If the information is not directly available in the context, "
                        f"respond with: 'I'm sorry, but I cannot find that information within the Zoomer Africa knowledge base.'\n\n"
                        f"Context:\n{context}"
                    )
                },
                {"role": "user", "content": user_input}
            ]
            response = client.chat.completions.create(
                model="Qwen/Qwen3-8B",
                messages=messages,
                max_tokens=200, # Limit response length
                temperature=0.2, # Reduce randomness for more factual answers
                top_p=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error getting response: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}. Please try again later."

# Initialize assistant globally
print("Initializing AfroZoomer assistant...")
assistant = AfroZoomerAssistant()
print("AfroZoomer is ready!")

# ========== Flask Routes ==========

@app.route('/')
def home():
    return render_template("zoomer.html")

@app.route('/ask', methods=['POST'])
def ask():
    try:
        user_input = request.form['user_input']
        response = assistant.get_response(user_input)
        return jsonify({'response': response})
    except Exception as e:
        print("Fatal error in /ask:", e)
        return jsonify({'response': "Oops! Internal assistant error."}), 500

if __name__ == "__main__":
    # Listen on the right port for Render
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
