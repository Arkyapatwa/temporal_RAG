import asyncio
import argparse
from temporalio.client import Client
from workflows.document_workflow import DocumentWorkFlow
from models.document_model import FileModel
import os
from dotenv import load_dotenv

load_dotenv()

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")

async def start_workflow(file_id: str, file_url: str):
    client = await Client.connect(TEMPORAL_HOST)

    file = FileModel(id=file_id, link=file_url)

    result = await client.start_workflow(
        DocumentWorkFlow.run,
        file,
        id=f"file-processing-{file_id}",
        task_queue="document-queue"
    )

    print(f"Workflow result: {result}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a file processing workflow.")
    parser.add_argument("file_id", type=str, help="The unique ID of the file.")
    parser.add_argument("file_url", type=str, help="The URL of the file to process.")

    args = parser.parse_args()

    asyncio.run(start_workflow(args.file_id, args.file_url))
