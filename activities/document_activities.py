from temporalio import activity

from unstructured.documents.elements import Element

from models.document_model import FileModel

from typing import List, Tuple

import asyncio, uuid
from io import BytesIO

chunked_Elements = {}

@activity.defn
async def fetch_document_activity(fileInput: FileModel) -> Tuple[bytes, str]:
    activity.logger.info("Fetching document from %s" % fileInput.link)
    import httpx
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(fileInput.link)
            response.raise_for_status()
            
            activity.logger.info("Fetched document from %s" % fileInput.link)
            file_data = BytesIO(response.content)
            file_name = fileInput.link.split("/")[-1]
            return file_data.getvalue(), file_name
        except httpx.HTTPStatusError as e:
            activity.logger.error(e.response.json())
            
        except httpx.NetworkError as e:
            activity.logger.error(e)
            
        

@activity.defn
async def parse_document_activity(file_info: Tuple[bytes, str]) -> str:
    data, file_name = file_info
    activity.logger.info(f"Parsing document ")
    file_data = BytesIO(data)

    file_data.seek(0)
    file_type = file_name.split(".")[-1]
    
    supported_types = ["pdf", "docx", "doc", "xlsx", "xls", "txt"]
    if file_type not in supported_types:
        activity.logger.error("Unsupported file type %s" % file_type)
        raise Exception("Unsupported file type %s" % file_type)
    
    try:
        from unstructured.partition import pdf, text, docx, doc, xlsx
        from unstructured.chunking.title import chunk_by_title
        
        if file_type == "pdf":
            parts = pdf.partition_pdf(file=file_data)
        elif file_type == "docx":
            parts = docx.partition_docx(file=file_data)
        elif file_type == "doc":
            parts = doc.partition_doc(file=file_data)
        elif file_type == "xlsx":
            parts = xlsx.partition_xlsx(file=file_data)
        elif file_type == "xls":
            parts = xlsx.partition_xlsx(file=file_data)
        elif file_type == "txt":
            parts = text.partition_text(file=file_data)
            
        if parts is None:
            activity.logger.error("No content found")
            raise Exception("No content found")
        
        activity.logger.info("Parsed document into %s parts" % len(parts))
        elements_id = str(uuid.uuid4())
        chunked_Elements[elements_id] = chunk_by_title(elements=parts)
        
        return elements_id        
        
    except Exception as e:
        activity.logger.error(e)
        
    
    
@activity.defn
async def embeddings_document_activity(elements_id: str, batch_size: int = 10) -> str:
    activity.logger.info("Embedding document")
    from openai_connections import OpenAIConnection
    openai_connection = OpenAIConnection()
    elements = chunked_Elements[elements_id]
    
    try:
        tasks = []
        for i in range(0, len(elements), batch_size):
            chunk = elements[i:i+batch_size]
            tasks.append(openai_connection.create_embed_docs(chunk))
            
        results_batched = await asyncio.gather(*tasks)
        activity.logger.info("Embedded document into %s parts" % len(results_batched))
        chunked_Elements[elements_id] = [element for elements in results_batched for element in elements]
        return str(elements_id)
            
    except Exception as e:
        activity.logger.error(e)
        
    

@activity.defn
async def store_document_activity(elements_id: str, batch_size: int = 100, max_concurrent_tasks: int = 10) -> str:
    from db_connection import MilvusConnection
    db_connection = MilvusConnection()
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    
    elements = chunked_Elements[elements_id]
    
    try:
        activity.logger.info("Storing document")
        tasks = []
        for i in range(0, len(elements), batch_size):
            chunk = elements[i:i+batch_size]
            tasks.append(db_connection.add_embeddings_batch(chunk, semaphore))
            
        await asyncio.gather(*tasks)
        activity.logger.info("Stored document into %s parts" % len(elements))
        return "Stored document into %s parts" % len(elements)
            
    except Exception as e:
        activity.logger.error(e)
        