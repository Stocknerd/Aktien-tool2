import os
import json
import glob

# Try to import Langchain components, handling gracefully if they aren't installed yet
try:
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_core.documents import Document
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

DATA_DIR = os.path.abspath('data/raw')
INDEX_DIR = os.path.abspath('data/faiss_index')

def build_index():
    if not LANGCHAIN_AVAILABLE:
        print("Error: LangChain or OpenAI is not installed.")
        return
        
    print("Building RAG index from raw JSON data...")
    if not os.path.exists(INDEX_DIR):
        os.makedirs(INDEX_DIR)
        
    embeddings = OpenAIEmbeddings()
    docs = []
    
    files = glob.glob(os.path.join(DATA_DIR, '*.json'))
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                symbol = data.get('Symbol', os.path.basename(f).replace('.json', ''))
                # Create a textual representation of fundamental data
                text_content = f"Aktie: {data.get('Security', symbol)} (Ticker: {symbol}).\n"
                for k, v in data.items():
                    if k not in ['Symbol', 'Security', 'logo_url'] and v is not None:
                        text_content += f"{k}: {v}\n"
                        
                docs.append(Document(page_content=text_content, metadata={"symbol": symbol}))
            except Exception as e:
                print(f"Error loading {f}: {e}")
                
    if not docs:
        print("No documents found in data/raw.")
        return
        
    print(f"Loaded {len(docs)} documents. Embedding ...")
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(INDEX_DIR)
    print(f"Index successfully saved to {INDEX_DIR}")


def get_retriever():
    if not LANGCHAIN_AVAILABLE:
        raise RuntimeError("LangChain not available")
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_kwargs={"k": 3})


def generate_analysis(ticker: str) -> str:
    """R3: AI-basierte Aktienanalyse basierend auf Rohdaten."""
    if not LANGCHAIN_AVAILABLE:
        return "Error: LangChain is not installed."
        
    try:
        retriever = get_retriever()
    except Exception as e:
        return f"Fehler beim Laden des FAISS-Index ({INDEX_DIR}). Hast du den Index vorher gebaut? error: {e}"

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    template = """Du bist ein erfahrener Finanzanalyst.
    Nutze die folgenden Fundamentaldaten aus unserer Datenbank, um eine prägnante, professionelle Aktienanalyse für den Ticker {ticker} zu schreiben.
    Gehe auf Bewertung (KGV, KBV), Wachstum, Rentabilität und Dividende ein. Setze es in den Kontext des Sektors, wenn möglich. 
    Beende die Analyse mit einem klaren Fazit.
    Falls keine relevanten Daten vorliegen, teile dies mit.

    Kontextdaten:
    {context}

    Analyse für {ticker}:
    """
    prompt = PromptTemplate.from_template(template)
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
        
    rag_chain = (
        {"context": retriever | format_docs, "ticker": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    print(f"Generating AI analysis for {ticker}...")
    return rag_chain.invoke(ticker)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        if not os.environ.get("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY environment variable not set. Required for embeddings.")
            sys.exit(1)
        build_index()
    elif len(sys.argv) > 2 and sys.argv[1] == "analyze":
        if not os.environ.get("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY environment variable not set.")
            sys.exit(1)
        print("\n" + generate_analysis(sys.argv[2]) + "\n")
    else:
        print("Usage:")
        print("  python ai_rag.py build          # Index bauen aus data/raw/*.json")
        print("  python ai_rag.py analyze TSLA   # Analyse generieren")
