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

# ===== Load and Embed Zoomer Africa FAQ =====
doc = Document("zoomer_faqs.docx")
faq_chunks = [para.text.strip() for para in doc.paragraphs if para.text.strip()][:50]  # Limit to 50 chunks for now

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
        self.faq_chunks = faq_chunks  # Use global faq_chunks
        
        # Get dimension from sample
        sample_emb = get_embedding("sample")
        self.embedding_dim = len(sample_emb)
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Process chunks in small batches to avoid rate limits
        all_embeddings = []
        batch_size = 2  # Reduced to limit memory usage
        
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
            relevant_faqs = [self.faq_chunks[i][:300] for i in I[0] if i < len(self.faq_chunks)]
            return "\n".join(relevant_faqs[:2])
        except Exception as e:
            print(f"Error getting contextual FAQ: {e}")
            # Fallback to returning first few FAQs
            return "\n".join(self.faq_chunks[:3])

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_response(self, user_input):
        try:
            context = self.get_contextual_faq(user_input)

            # Add latest user message to history
            self.conversation_history.append({"role": "user", "content": user_input})

            # Trim to last 3 turns (user + assistant = 6 messages max)
            max_turns = 2
            if len(self.conversation_history) > max_turns * 2:
                self.conversation_history = self.conversation_history[-max_turns * 2:]

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are AfroZoomer, an assistant for Zoomer Africa. "
                        "Answer users greetings with a friendly tone. and ask them how you can help. "
                        "If a user greets you, greet them back with a friendly tone (you can include some emojis to show happiness) and strictly ask them how you can assist them, you can give them a few they can inquire from you about Zoomer Africa, without explaining too much. "
                        "If a user show sad feelings you can confort a user if they are sad or angry about zoomer africa, maybe from an issue (show some sympathy maybe through use of emoji and provide a helpful advice), and ask them how you can help. "
                        "Provide helpful and accurate answers, but keep them short and summarized "
                        "so users on mobile can quickly understand. If needed, provide a short example or pro tip."
                        "Aim to answer clearly in under 200 words. Avoid unnecessary elaboration."
                        "Contextual facts:\n"
                            "1. The founders of Zoomer Africa are Mr. Oweka Bob – Developer & Founder from Kampala-Uganda, Mr. Huzayiru Kalungi – Chief Executive Officer (CEO) from Kampala-Uganda, Mr. Mowat Taurus – Chief Operation Officer (COO) from Kampala-Uganda, and Mr. Odongo Emmanuel – Chief Marketing Officer & Data Analyst (CMO) from Nairobi-Kenya, Mr. Wanyama Benard – Executive member from Kampala-Uganda.\n"
                            "2. While the exact launch date of Zoomer Africa isn't explicitly stated, the copyright year on the website is 2025, indicating it is either a newly launched platform or was in its final stages of development around that time.\n"
                            "3. The company behind Zoomer Africa platform is called Transparent Hub Uganda Limited (THUL), Kampala Uganda.\n"
                            "4. The official website of Zoomer Africa is https://zoomer.africa, this is registered domain and it's the official one. Only provide it if necessary\n"
                            

                    )
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_input}"}
            ] + self.conversation_history

            response = client.chat.completions.create(
                model="Qwen/Qwen3-8B",
                messages=messages,
                max_tokens=800,
                temperature=0.6,
                top_p=0.9,
            )
            reply = response.choices[0].message.content.strip()
            self.conversation_history.append({"role": "assistant", "content": reply})

            return reply
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
