import os
import time
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google import genai
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings
from typing import List

# Load environment variables from .env file in campus directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("ERROR: API_KEY not found in .env file at: " + env_path)
    exit(1)

# Configure the new genai client
client = genai.Client(api_key=API_KEY)

# Custom embeddings class using the new genai API with batch processing and rate limiting
class GenAIEmbeddings(Embeddings):
    def __init__(self, client):
        self.client = client
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for i, text in enumerate(texts):
            try:
                result = self.client.models.embed_content(
                    model="models/text-embedding-004",
                    contents=text
                )
                embeddings.append(result.embeddings[0].values)
                
                # Add small delay to avoid rate limiting (every 10 requests)
                if (i + 1) % 10 == 0:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Warning: Error embedding document {i+1}: {e}")
                # Use zero vector as fallback
                embeddings.append([0.0] * 768)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        result = self.client.models.embed_content(
            model="models/text-embedding-004",
            contents=text
        )
        return result.embeddings[0].values

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        total_pages = len(pdf_reader.pages)
        print(f"Extracting text from {total_pages} pages...")
        
        for i, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text += page_text
            if i % 10 == 0:  # Progress indicator
                print(f"Processed {i}/{total_pages} pages...")
    
    print(f"✓ Extracted {len(text)} characters from PDF")
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    print(f"✓ Created {len(chunks)} text chunks")
    return chunks

def get_vector_store(text_chunks):
    print(f"Creating embeddings for {len(text_chunks)} chunks...")
    embeddings = GenAIEmbeddings(client)
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")  # This creates the index
    print("✓ Vector store created and saved")

def load_vector_store(embeddings):
    try:
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        return new_db
    except FileNotFoundError:
        print("ERROR: FAISS index not found. Please create it by processing PDF files first.")
        return None

def get_answer_from_context(context, question):
    prompt = f"""
    Answer the question in as detailed manner as possible from the provided context. Make sure to provide all the details. If the answer is not in the provided
    context, then just say, "answer is not available in the context." Don't provide the wrong answer.
    
    Context:
    {context}
    
    Question:
    {question}
    
    Answer:
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    return response.text

def user_input(user_question, num_results=4):
    embeddings = GenAIEmbeddings(client)
    new_db = load_vector_store(embeddings)
    if new_db is None:  # If the index couldn't be loaded, exit early
        return None

    # Search for relevant documents
    docs = new_db.similarity_search(user_question, k=num_results)
    
    if not docs:
        return "No relevant information found in the PDF."
    
    # Combine all document contents into context
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Get answer using the new API
    answer = get_answer_from_context(context, user_question)
    
    return answer

def main():
    print("=" * 60)
    print("PDF Chatbot - Terminal Version")
    print("Powered by Google Gemini 2.5 Flash")
    print("=" * 60)
    
    # Check if FAISS index exists
    if os.path.exists("faiss_index"):
        print("✓ Found existing PDF index")
    else:
        print("⚠ No PDF index found. Please process a PDF first.")
    
    while True:
        print("\nOptions:")
        print("1. Process a PDF file")
        print("2. Ask a question about the processed PDF")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            pdf_path = input("\nEnter the path to your PDF file (or just filename if in current folder): ").strip()
            
            # If just a filename is provided, look in the current directory
            if not os.path.isabs(pdf_path):
                pdf_path = os.path.join(os.path.dirname(__file__), pdf_path)
            
            if not os.path.exists(pdf_path):
                print(f"ERROR: File not found at {pdf_path}")
                continue
            
            if not pdf_path.lower().endswith('.pdf'):
                print("ERROR: Please provide a valid PDF file.")
                continue
            
            try:
                print("\n" + "=" * 60)
                print("Processing PDF...")
                print("=" * 60)
                
                start_time = time.time()
                raw_text = get_pdf_text([pdf_path])
                
                if not raw_text.strip():
                    print("ERROR: No text extracted from PDF. The PDF might be image-based or empty.")
                    continue
                
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                
                elapsed_time = time.time() - start_time
                print(f"\n✓ Done processing the PDF in {elapsed_time:.2f} seconds!")
                
            except Exception as e:
                print(f"ERROR: Error processing the PDF file: {e}")
        
        elif choice == "2":
            user_question = input("\nAsk a Question about the PDF: ").strip()
            
            if not user_question:
                print("ERROR: Please enter a valid question.")
                continue
            
            try:
                print("\nSearching for answer...")
                answer = user_input(user_question)
                if answer:
                    print("\n" + "=" * 60)
                    print("Answer:")
                    print("=" * 60)
                    print(answer)
                    print("=" * 60)
            except Exception as e:
                print(f"ERROR: {e}")
        
        elif choice == "3":
            print("\nGoodbye!")
            break
        
        else:
            print("ERROR: Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
