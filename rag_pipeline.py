import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Global variables to hold our RAG components
vector_store = None
qa_chain = None

def init_rag():
    """Initializes the Vector Database and the RAG pipeline."""
    global vector_store, qa_chain
    try:
        # 1. Load the FAQ document
        faq_path = os.path.join(os.path.dirname(__file__), "data", "college_faq.txt")
        loader = TextLoader(faq_path)
        docs = loader.load()

        # 2. Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)

        # 3. Initialize Gemini Embeddings
        # Ensure GEMINI_API_KEY is available in environment
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

        # 4. Create and persist the FAISS Vector Store
        persist_dir = os.path.join(os.path.dirname(__file__), "faiss_index")
        if os.path.exists(persist_dir):
            vector_store = FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)
        else:
            vector_store = FAISS.from_documents(documents=splits, embedding=embeddings)
            vector_store.save_local(persist_dir)

        # 5. Set up LLM and Chains
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
        
        system_prompt = (
            "You are a helpful college assistant. Use the given context to answer the user's question. "
            "If you don't know the answer based on the context, say that you don't know and advise them "
            "to contact administration. Be concise and polite.\n\n"
            "Context: {context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        qa_chain = create_retrieval_chain(retriever, question_answer_chain)
        print("RAG Pipeline initialized successfully.")
    except Exception as e:
        print(f"Error initializing RAG: {e}")

def ask_question(question: str) -> dict:
    """Answers a question using the initialized RAG chain and returns answer with sources."""
    if not qa_chain:
        return {"answer": "The RAG pipeline is not initialized.", "sources": []}
    try:
        result = qa_chain.invoke({"input": question})
        answer = result.get("answer", "No answer found.")
        
        # Extract sources from the "context" key
        context_docs = result.get("context", [])
        sources = [doc.page_content for doc in context_docs]
        
        return {"answer": answer, "sources": sources}
    except Exception as e:
        print(f"RAG Error: {e}")
        return {"answer": "Sorry, I encountered an error processing your query.", "sources": []}
