from temporalio.client import Client
from temporalio.worker import Worker

from workflows.document_workflow import DocumentWorkFlow
from activities.document_activities import fetch_document_activity, parse_document_activity, embeddings_document_activity, store_document_activity

from dotenv import load_dotenv
import os, asyncio

load_dotenv()

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")


async def main():
    temporal_client = await Client.connect(TEMPORAL_HOST)
    
    worker = Worker(
        client=temporal_client,
        task_queue="document-queue",
        workflows=[DocumentWorkFlow],
        activities=[
            fetch_document_activity, 
            parse_document_activity, 
            embeddings_document_activity, 
            store_document_activity
            ],
    )
    
    await worker.run()

asyncio.run(main())
    