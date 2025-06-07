from temporalio import activity
from unstructured.documents.elements import Element
from models.document_model import FileModel
from db_connection import MilvusConnection

from typing import List, Tuple, Dict
from dataclasses import dataclass

import asyncio
from io import BytesIO
import structlog

logger = structlog.get_logger()

@dataclass
class DocumentChunk:
    id: str
    elements: List[Element]

class DocumentProcessingError(Exception):
    pass

class StorageManager:
    def __init__(self):
        self.db = MilvusConnection()
        self.chunks: Dict[str, DocumentChunk] = {}
    
    def store_chunk(self, chunk_id: str, elements: List[Element]) -> None:
        self.chunks[chunk_id] = DocumentChunk(id=chunk_id, elements=elements)
    
    def get_chunk(self, chunk_id: str) -> List[Element]:
        chunk = self.chunks.get(chunk_id)
        if not chunk:
            raise DocumentProcessingError(f"Chunk {chunk_id} not found")
        return chunk.elements
    
    def update_chunk(self, chunk_id: str, elements: List[Element]) -> None:
        if chunk_id not in self.chunks:
            raise DocumentProcessingError(f"Chunk {chunk_id} not found")
        self.chunks[chunk_id] = DocumentChunk(id=chunk_id, elements=elements)
    
    async def cleanup(self) -> None:
        await self.db.cleanup()
        self.chunks.clear()

storage = StorageManager()

@activity.defn
async def fetch_document_activity(fileInput: FileModel) -> Tuple[bytes, str, str]:
    log = logger.bind(activity="fetch_document", file_id=fileInput.id)
    log.info("starting_document_fetch", url=fileInput.link)
    
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(fileInput.link)
            response.raise_for_status()
            
            file_data = BytesIO(response.content)
            file_name = fileInput.link.split("/")[-1]
            
            log.info("document_fetch_complete", 
                     file_name=file_name, 
                     size_bytes=len(response.content))
            
            return file_data.getvalue(), file_name, fileInput.id
            
        except httpx.HTTPStatusError as e:
            log.error("http_error_during_fetch", 
                      status_code=e.response.status_code,
                      error_detail=e.response.text)
            raise DocumentProcessingError(f"HTTP error {e.response.status_code}: {e.response.text}")
            
        except httpx.NetworkError as e:
            log.error("network_error_during_fetch", error=str(e))
            raise DocumentProcessingError(f"Network error: {str(e)}")
            
        

@activity.defn
async def parse_document_activity(file_info: Tuple[bytes, str, str]) -> str:
    data, file_name, file_id = file_info
    log = logger.bind(activity="parse_document", file_name=file_name)
    log.info("starting_document_parse")
    
    file_data = BytesIO(data)
    file_data.seek(0)
    file_type = file_name.split(".")[-1].lower()
    
    supported_types = ["pdf", "docx", "doc", "xlsx", "xls", "txt"]
    if file_type not in supported_types:
        log.error("unsupported_file_type", file_type=file_type)
        raise DocumentProcessingError(f"Unsupported file type: {file_type}")
    
    try:
        from unstructured.partition import pdf, text, docx, doc, xlsx
        from unstructured.chunking.title import chunk_by_title
        
        partition_funcs = {
            "pdf": pdf.partition_pdf,
            "docx": docx.partition_docx,
            "doc": doc.partition_doc,
            "xlsx": xlsx.partition_xlsx,
            "xls": xlsx.partition_xlsx,
            "txt": text.partition_text
        }
        
        parts = partition_funcs[file_type](file=file_data)
        
        if not parts:
            log.error("no_content_found")
            raise DocumentProcessingError("No content found in document")
        
        elements = chunk_by_title(elements=parts)
        elements_id = file_id
        
        storage.store_chunk(elements_id, elements)
        
        log.info("document_parse_complete", 
                 chunk_id=elements_id,
                 num_parts=len(parts),
                 num_elements=len(elements))
        
        return elements_id
        
    except DocumentProcessingError:
        raise
    except Exception as e:
        log.error("parse_error", error=str(e))
        raise DocumentProcessingError(f"Error parsing document: {str(e)}")
        
    
    
@activity.defn
async def embeddings_document_activity(elements_id: str, batch_size: int = 10) -> str:
    log = logger.bind(activity="embeddings_document", chunk_id=elements_id)
    log.info("starting_document_embedding", batch_size=batch_size)
    
    try:
        from openai_connections import OpenAIConnection
        openai_connection = OpenAIConnection()
        elements = storage.get_chunk(elements_id)
        
        if not elements:
            logger.error("No elements found for storage")
            raise DocumentProcessingError("No elements found for embedding")
        
        tasks = []
        for i in range(0, len(elements), batch_size):
            chunk = elements[i:i+batch_size]
            tasks.append(openai_connection.create_embed_docs(chunk))
        
        try:
            results_batched = await asyncio.gather(*tasks)
            embedded_elements = [element for elements in results_batched for element in elements]
            
            if not embedded_elements:
                log.error("embedding_produced_no_results")
                raise DocumentProcessingError("Embedding process produced no results")
            
            storage.update_chunk(elements_id, embedded_elements)
            
            log.info("document_embedding_complete",
                     num_elements=len(embedded_elements),
                     num_batches=len(results_batched))
            
            return elements_id
            
        except asyncio.TimeoutError as e:
            log.error("embedding_timeout", error=str(e))
            raise DocumentProcessingError("Embedding process timed out")
            
    except DocumentProcessingError:
        raise
    except Exception as e:
        log.error("embedding_error", error=str(e))
        raise DocumentProcessingError(f"Error during embedding: {str(e)}")
        
    

@activity.defn
async def store_document_activity(elements_id: str, batch_size: int = 10, max_concurrent_tasks: int = 5) -> str:
    log = logger.bind(activity="store_document", chunk_id=elements_id)
    log.info("starting_document_storage",
             batch_size=batch_size,
             max_concurrent_tasks=max_concurrent_tasks)
    
    try:
        elements = storage.get_chunk(elements_id)
        
        if not elements:
            logger.error("No elements found for storage")
            raise DocumentProcessingError("No elements found for storage")
        
        semaphore = asyncio.Semaphore(max_concurrent_tasks)
        tasks = []
        for i in range(0, len(elements), batch_size):
            chunk = elements[i:i+batch_size]
            tasks.append(asyncio.create_task(MilvusConnection().add_embeddings_batch(chunk, semaphore)))
        
        try:
            await asyncio.gather(*tasks)
            
            log.info("document_storage_complete",
                     total_elements=len(elements),
                     num_batches=len(tasks))
            
            return f"Successfully stored {len(elements)} elements in {len(tasks)} batches"
            
        except asyncio.TimeoutError as e:
            logger.error(f"Storage operation timed out: {str(e)}")
            raise DocumentProcessingError("Storage operation timed out")
            
    except DocumentProcessingError:
        raise
    except Exception as e:
            logger.error(f"Error during storage: {str(e)}")
            raise DocumentProcessingError(f"Error during storage: {str(e)}")
        