
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
        # check if db exists
        if DB_NAME not in self.milvus_client.list_databases():
            self.milvus_client.create_database(DB_NAME)
            
        self.milvus_client.use_database(DB_NAME)
        if not self.milvus_client.has_collection(COLLECTION_NAME):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="element_id", dtype=DataType.VARCHAR, max_length=36),
                FieldSchema(name="file_id", dtype=DataType.VARCHAR, max_length=36),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=3072),  # Adjust dimension
            ]
            schema = CollectionSchema(fields, description="Collection for large dataset")
            self.milvus_client.create_collection(collection_name=COLLECTION_NAME, schema=schema)
            
            self.create_index()
    
    def get_milvus_client(self) -> MilvusClient:
        return self.milvus_client

    async def add_embeddings_batch(self, file_id: str, elements: List[Element], semaphore) -> str:
        if not elements:
            return

        try:
            async with semaphore:
                # element_id = []
                # text = []
                # metadata = []
                # embedding = []
                
                data = []
                
                for element in elements:
                        
                    # element_id.append(element.id)
                    # text.append(element.text)
                    # embedding.append(element.embeddings)
                    data.append(
                        {
                            "element_id": element.id,
                            "file_id": file_id,
                            "text": element.text,
                            "embeddings": element.embeddings
                        }
                    )
                # if not element_id:
                #     return
                
                
                self.milvus_client.insert(data=data, collection_name=COLLECTION_NAME)
                return "Successfully added embeddings to Milvus"
        except Exception as e:
            raise

    def create_index(self):
        index_params = MilvusClient.prepare_index_params()

        # 4.2. Add an index on the vector field.
        index_params.add_index(
            field_name="embeddings",
            metric_type="COSINE",
            index_type="IVF_FLAT",
            index_name="vector_index",
            params={ "nlist": 128 }
        )

        # 4.3. Create an index file
        self.milvus_client.create_index(
            collection_name=COLLECTION_NAME,
            index_params=index_params,
            sync=False # Whether to wait for index creation to complete before returning. Defaults to True.
        )


    
        