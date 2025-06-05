
from unstructured.embed.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingEncoder
from unstructured.documents.elements import Element
from pydantic import SecretStr

import os
from dotenv import load_dotenv
from threading import Lock
from typing import List

load_dotenv()


os.environ["OPENAI_API_KEY"] = os.getenv("GITHUB_TOKEN")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT")

os.environ["OPENAI_API_BASE"] = EMBEDDING_ENDPOINT

class OpenAIConnection:
    
    __instance = None
    __lock = Lock()
    
    def __new__(cls):
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = super().__new__(cls)
        return cls.__instance
    
    def __init__(self):
        embedding_config = OpenAIEmbeddingConfig(
            api_key=SecretStr(GITHUB_TOKEN),
            model_name=EMBEDDING_MODEL,
        )
        
        self.embedding_model = OpenAIEmbeddingEncoder(config=embedding_config)

    def get_embeddings_model(self):
        return self.embedding_model
    
    async def create_embed_docs(self, elements: List[Element]) -> List[Element]:
        try:
            return self.embedding_model.embed_documents(elements)
        except Exception as e:
            print(e)
        