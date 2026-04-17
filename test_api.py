import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Test 1: Chat model
print("--- Test 1: gemini-2.0-flash ---")
try:
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Say hello in one word")
    print(f"OK: {response.text.strip()}")
except Exception as e:
    print(f"FAIL: {e}")

# Test 2: Embedding model
print("--- Test 2: gemini-embedding-001 ---")
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    result = embeddings.embed_query("test query")
    print(f"OK: embedding length = {len(result)}")
except Exception as e:
    print(f"FAIL: {e}")

print("--- DONE ---")
