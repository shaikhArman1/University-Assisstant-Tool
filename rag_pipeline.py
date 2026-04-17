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

# Global variables
vector_store = None
qa_chain = None


def init_rag():
    """Initializes the Vector Database and the RAG pipeline."""
    global vector_store, qa_chain

    try:
        # 1. Load document
        faq_path = os.path.join(os.path.dirname(__file__), "data", "college_faq.txt")
        loader = TextLoader(faq_path)
        docs = loader.load()

        # 2. Split document
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100
        )
        splits = text_splitter.split_documents(docs)

        # 3. Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )

        # 4. Vector store (FAISS)
        persist_dir = os.path.join(os.path.dirname(__file__), "faiss_index")

        if os.path.exists(persist_dir):
            print("Loading FAISS from disk...")
            vector_store = FAISS.load_local(
                persist_dir,
                embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print("Creating FAISS index...")
            vector_store = FAISS.from_documents(splits, embeddings)
            vector_store.save_local(persist_dir)

        # 5. LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",   # faster
            temperature=0.3
        )

        # 6. Strong Prompt
        system_prompt = """
You are a highly accurate University Assistant.

RULES:
1. Use ONLY the given context.
2. Give COMPLETE answers — do not give partial sentences.
3. Combine all relevant information from context.
4. NEVER dump raw text.

FORMAT:
- Answer in 2–4 bullet points
- Be clear and complete
- Highlight key info (timings, fees, dates)

If not found:
"I couldn't find complete information in the provided data."

CONTEXT:
{context}

QUESTION:
{input}

FINAL ANSWER:
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])

        # 7. Chains
        question_answer_chain = create_stuff_documents_chain(llm, prompt)

        retriever = vector_store.as_retriever(
            search_kwargs={"k": 4}
        )

        qa_chain = create_retrieval_chain(retriever, question_answer_chain)

        print("✅ RAG Pipeline initialized successfully.")

    except Exception as e:
        print(f"❌ Error initializing RAG: {e}")


def ask_question(question: str) -> dict:
    """Answers a question using RAG and returns answer + sources."""

    if not qa_chain:
        return {
            "answer": "The RAG pipeline is not initialized.",
            "sources": []
        }

    try:
        result = qa_chain.invoke({"input": question})

        answer = result.get("answer", "No answer found.")
        answer = answer.strip().replace("\n\n", "\n")

        # Clean sources
        context_docs = result.get("context", [])
        sources = list(set([
            doc.page_content[:120].strip().split("\n")[0]
            for doc in context_docs
        ]))

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        print(f"RAG Error: {e}")
        return {
            "answer": "Sorry, I encountered an error processing your query.",
            "sources": []
        }