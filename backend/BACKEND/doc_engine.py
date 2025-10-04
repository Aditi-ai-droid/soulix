import os
from llama_index import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI as LlamaOpenAI

# Initialize LLM
llama_llm = LlamaOpenAI(
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Load documents from 'data' folder
documents = SimpleDirectoryReader('data').load_data()

# Create vector index from documents
index = VectorStoreIndex.from_documents(documents)  # ✅ corrected 'form_documents' -> 'from_documents'

# Create a query engine using the index
query_engine = index.as_query_engine(llm=llama_llm)

# Function to query documents
def query_documents(user_query: str) -> str:
    return str(query_engine.query(user_query))
