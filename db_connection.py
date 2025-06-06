
from pymilvus import MilvusClient, DataType, FieldSchema, CollectionSchema
from unstructured.documents.elements import Element

import os
from dotenv import load_dotenv
from threading import Lock
from typing import List
import json

load_dotenv()


MILVUS_HOST = os.getenv("MILVUS_HOST")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
COLLECTION_NAME_ELEMENTS = os.getenv("COLLECTION_NAME_ELEMENTS")
DB_NAME = os.getenv("DB_NAME")

class MilvusConnection:
    
    __instance = None
    __lock = Lock()
    
    def __new__(cls):
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = super().__new__(cls)
        return cls.__instance
    
    def __init__(self):
        self.milvus_client = MilvusClient(host=MILVUS_HOST)
        self.milvus_client.create_database(db_name=DB_NAME)
        if not self.milvus_client.has_collection(COLLECTION_NAME):
            
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="element_id", dtype=DataType.VARCHAR, max_length=36),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=1000),  # JSON-encoded string
                FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=9),  # Adjust dimension
            ]
            schema = CollectionSchema(fields, description="Collection for large dataset")
            self.milvus_client.create_collection(collection_name=COLLECTION_NAME, schema=schema)
    
    def get_milvus_client(self) -> MilvusClient:
        return self.milvus_client
    
    async def add_embeddings_batch(self, elements: List[Element], semaphore) -> None:
        try:
            async with semaphore:
                element_id = []
                text = []
                metadata = []
                embedding = []
                for element in elements:
                    element_id.append(element.id)
                    text.append(element.text)
                    metadata.append(json.dumps(element.metadata))
                    embedding.append(element.embeddings)
                
                data = {
                    "element_id": element_id,
                    "text": text,
                    "metadata": metadata,
                    "embeddings": embedding
                }
                    
                self.milvus_client.insert(data=data, collection_name=COLLECTION_NAME)
        except Exception as e:
            raise e


    
        