import os
import time
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from typing import List
from dotenv import load_dotenv
import hashlib

# Load .env from the campus directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

API_KEY = os.getenv("API_KEY")

# Validate API key
if not API_KEY:
    raise ValueError("API_KEY not found in environment variables. Please check your .env file at: " + env_path)

# Configure the genai client
client = genai.Client(api_key=API_KEY)

# Custom embeddings class using the new genai API
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
                
                # Add small delay to avoid rate limiting
                if (i + 1) % 10 == 0:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Warning: Error embedding document {i+1}: {e}")
                embeddings.append([0.0] * 768)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        result = self.client.models.embed_content(
            model="models/text-embedding-004",
            contents=text
        )
        return result.embeddings[0].values

def get_pdf_text_from_path(pdf_path):
    """Extract text from a PDF file path - optimized for large files"""
    text = ""
    try:
        pdf_reader = PdfReader(pdf_path)
        total_pages = len(pdf_reader.pages)
        
        # Process in chunks for large PDFs
        for i, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                # Log progress for large files
                if total_pages > 50 and (i + 1) % 50 == 0:
                    print(f"Processing PDF: {i + 1}/{total_pages} pages...")
                    
            except Exception as e:
                print(f"Warning: Could not extract text from page {i + 1}: {e}")
                continue
        
        print(f"Successfully extracted text from {total_pages} pages")
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def get_text_chunks(text):
    """Split text into chunks - optimized for large documents"""
    # Increase chunk size for better context with large documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=15000,  # Increased from 10000
        chunk_overlap=2000,  # Increased from 1000
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    print(f"Split document into {len(chunks)} chunks")
    return chunks

def get_pdf_hash(pdf_path):
    """Generate a unique hash for the PDF file"""
    with open(pdf_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_vector_store_for_pdf(pdf_path, index_folder="faiss_indices"):
    """Create or load vector store for a specific PDF"""
    pdf_hash = get_pdf_hash(pdf_path)
    index_path = os.path.join(index_folder, f"faiss_index_{pdf_hash}")
    
    embeddings = GenAIEmbeddings(client)
    
    # Check if index already exists
    if os.path.exists(index_path):
        try:
            vector_store = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            return vector_store
        except:
            pass  # If loading fails, create new one
    
    # Create new vector store with optimized processing
    print(f"Processing PDF: {pdf_path}")
    raw_text = get_pdf_text_from_path(pdf_path)
    if not raw_text.strip():
        print("Error: No text extracted from PDF")
        return None
    
    print(f"Extracted {len(raw_text)} characters from PDF")
    text_chunks = get_text_chunks(raw_text)
    
    # Process embeddings in batches for large documents
    print(f"Creating embeddings for {len(text_chunks)} chunks...")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local(index_path)
    print(f"Vector store created and saved to {index_path}")
    
    return vector_store

def get_answer_from_context(context, question, chat_history=""):
    """Get answer from context with chat history"""
    history_text = ""
    if chat_history:
        history_text = f"\nPrevious conversation:\n{chat_history}\n"
    
    prompt = f"""
    Answer the question in a detailed manner from the provided context. Make sure to provide all the details. 
    If the answer is not in the provided context, then just say, "answer is not available in the context." 
    Don't provide the wrong answer.
    {history_text}
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

def get_answer_for_pdf(pdf_path, question, chat_history=""):
    """Get answer for a question about a specific PDF - optimized for large documents"""
    try:
        embeddings = GenAIEmbeddings(client)
        vector_store = get_vector_store_for_pdf(pdf_path)
        
        if vector_store is None:
            return "Error: Could not process the PDF file. The file may be too large or corrupted."
        
        # Search for more relevant documents for better context in large PDFs
        docs = vector_store.similarity_search(question, k=6)  # Increased from 4 to 6
        
        if not docs:
            return "No relevant information found in the PDF."
        
        # Combine all document contents into context
        context = "\n\n".join([doc.page_content for doc in docs])
        print(f"Retrieved {len(docs)} relevant chunks for question: {question[:50]}...")
        
        # Get answer with chat history
        answer = get_answer_from_context(context, question, chat_history)
        
        return answer
    except Exception as e:
        print(f"Error in get_answer_for_pdf: {str(e)}")
        return f"Error processing your question: {str(e)}"
