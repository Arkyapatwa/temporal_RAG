from temporalio import workflow
from datetime import timedelta

from models.document_model import FileModel
from activities import document_activities

workflow.defn(name="DocumentWorkFlow")
class DocumentWorkFlow:
    @workflow.run
    async def run(self, fileInput: FileModel):
        workflow.logger.info("Running workflow with parameter %s" % fileInput.id)
        
        fetch_document_activity = await workflow.execute_activity(
            document_activities.fetch_document_activity,
            fileInput,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        parse_document_activity = await workflow.execute_activity(
            document_activities.parse_document_activity,
            fetch_document_activity,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        embeddings_document_activity = await workflow.execute_activity(
            document_activities.embeddings_document_activity,
            parse_document_activity,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        store_document_activity = await workflow.execute_activity(
            document_activities.store_document_activity,
            embeddings_document_activity,
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        return store_document_activity