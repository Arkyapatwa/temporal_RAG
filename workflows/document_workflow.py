from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

from models.document_model import FileModel
from activities import document_activities

@workflow.defn(name="document-workflow", sandboxed=False)
class DocumentWorkFlow:
    @workflow.run
    async def run(self, fileInput: FileModel) -> str:
        workflow.logger.info("Running workflow with parameter %s" % fileInput.id)
        
        fetch_document_activity_data = await workflow.execute_activity(
            document_activities.fetch_document_activity,
            fileInput,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        parse_document_activity = await workflow.execute_activity(
            document_activities.parse_document_activity,
            fetch_document_activity_data,
            start_to_close_timeout=timedelta(seconds=20),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        
        embeddings_document_activity = await workflow.execute_activity(
            document_activities.embeddings_document_activity,
            parse_document_activity,
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        store_document_activity = await workflow.execute_activity(
            document_activities.store_document_activity,
            embeddings_document_activity,
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        return store_document_activity