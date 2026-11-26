
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from time import monotonic

from database.document_repository import (
    get_pending_documents,
    get_document_for_processing,
    retry_failed_document,
    recover_stale_documents,
)

from document_processor import process_document


router = APIRouter()

# Prevent overlapping processing jobs within this API process.
processing_lock = Lock()

# Prevent overlapping recovery checks.
recovery_check_lock = Lock()

# Avoid running a database recovery query on every status poll.
last_recovery_check = 0
RECOVERY_CHECK_INTERVAL_SECONDS = 30


def recover_stale_documents_if_idle():
    """
    Periodically recover stale documents, but only when
    no processing job is active in this API process.
    """

    global last_recovery_check

    if not recovery_check_lock.acquire(blocking=False):
        return 0

    try:
        current_time = monotonic()

        if (
            current_time - last_recovery_check
            < RECOVERY_CHECK_INTERVAL_SECONDS
        ):
            return 0

        # Do not recover documents while this API process
        # is actively processing a job.
        if not processing_lock.acquire(blocking=False):
            return 0

        try:
            recovered_count = recover_stale_documents(
                stale_after_minutes=30
            )

            last_recovery_check = monotonic()

            return recovered_count

        finally:
            processing_lock.release()

    finally:
        recovery_check_lock.release()

processing_state = {
    "is_running": False,
    "mode": None,
    "total": 0,
    "processed": 0,
    "completed": 0,
    "failed": 0,
    "current_document": None,

    # Overall and individual document progress.
    "progress_percent": 0,
    "current_document_progress": 0,

    # Current processing stage.
    "current_stage": None,
    "current_details": None,

    # Embedding progress.
    "completed_chunks": 0,
    "total_chunks": 0,
    "successful_chunks": 0,
    "failed_chunks": 0,
    "current_batch": 0,
    "total_batches": 0,
}


class BatchProcessingRequest(BaseModel):
    limit: int = Field(default=3, ge=1, le=5)


def update_document_progress(progress):
    """
    Update progress for the currently running document
    and calculate overall batch progress.
    """

    total = processing_state["total"]
    processed = processing_state["processed"]

    document_progress = progress["progress_percent"]

    processing_state.update({
        "current_document_progress": document_progress,
        "current_stage": progress["stage"],
        "current_details": progress.get("details"),

        "completed_chunks": progress.get("completed_chunks", 0),
        "total_chunks": progress.get("total_chunks", 0),
        "successful_chunks": progress.get("successful_chunks", 0),
        "failed_chunks": progress.get("failed_chunks", 0),
        "current_batch": progress.get("current_batch", 0),
        "total_batches": progress.get("total_batches", 0),
    })

    if total > 0:
        overall_progress = (
            (processed + document_progress / 100) / total
        ) * 100

        processing_state["progress_percent"] = round(
            overall_progress,
            2,
        )


def reset_document_progress():
    """
    Reset per-document progress before processing
    the next document.
    """

    processing_state.update({
        "current_document_progress": 0,
        "current_stage": "Starting",
        "current_details": "Preparing document for processing",

        "completed_chunks": 0,
        "total_chunks": 0,
        "successful_chunks": 0,
        "failed_chunks": 0,
        "current_batch": 0,
        "total_batches": 0,
    })


def initialize_processing_state(mode, total):
    """
    Initialize progress information for a new job.
    """

    processing_state.update({
        "is_running": True,
        "mode": mode,
        "total": total,
        "processed": 0,
        "completed": 0,
        "failed": 0,
        "current_document": None,
        "progress_percent": 0,
    })

    reset_document_progress()


def finish_processing():
    """
    Mark the processing job as finished.
    """

    processing_state.update({
        "is_running": False,
        "mode": None,
        "progress_percent": 100,
        "current_document_progress": 100,
        "current_stage": "Completed",
        "current_details": "Processing job finished",
        "current_document": None,
    })

    processing_lock.release()


def process_single_document(document_id, file_path):
    try:
        result = process_document(
            document_id=document_id,
            file_path=file_path,
            progress_callback=update_document_progress,
        )

        if result["status"] == "completed":
            processing_state["completed"] += 1

        elif result["status"] == "skipped":
            print(f"Document skipped: {document_id}")

    except Exception as error:
        processing_state["failed"] += 1
        processing_state["current_stage"] = "Failed"
        processing_state["current_details"] = str(error)

        print(f"Document processing failed: {error}")

    finally:
        processing_state["processed"] += 1
        finish_processing()


def process_batch_documents(documents):
    try:
        processing_state["total"] = len(documents)

        for index, document in enumerate(documents, start=1):

            document_id = document["document_id"]
            file_path = document["file_path"]

            processing_state["current_document"] = {
                "document_id": str(document_id),
                "title": document["title"],
            }

            reset_document_progress()

            print(
                f"\nProcessing batch document "
                f"{index}/{len(documents)}"
            )

            try:
                result = process_document(
                    document_id=document_id,
                    file_path=file_path,
                    progress_callback=update_document_progress,
                )

                if result["status"] == "completed":
                    processing_state["completed"] += 1

                elif result["status"] == "skipped":
                    print(f"Document skipped: {document_id}")

            except Exception as error:
                processing_state["failed"] += 1

                processing_state["current_stage"] = "Failed"
                processing_state["current_details"] = str(error)

                print(
                    f"Failed to process {document_id}: {error}"
                )

            finally:
                processing_state["processed"] += 1

                total = processing_state["total"]

                if total > 0:
                    processing_state["progress_percent"] = round(
                        (
                            processing_state["processed"] / total
                        ) * 100,
                        2,
                    )

        processing_state["current_details"] = (
            "All selected documents have been processed"
        )

    finally:
        finish_processing()


@router.post("/batch")
def start_batch_processing(
    request: BatchProcessingRequest,
    background_tasks: BackgroundTasks,
):
    if not processing_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another processing job is already running.",
        )

    try:
        # Recover documents abandoned by an interrupted process
        # before selecting the next pending batch.
        recover_stale_documents(stale_after_minutes=30)

        documents = get_pending_documents(limit=request.limit)

        if not documents:
            processing_lock.release()

            return {
                "status": "completed",
                "message": "No pending documents found.",
                "total": 0,
            }

        initialize_processing_state(
            mode="batch",
            total=len(documents),
        )

        background_tasks.add_task(
            process_batch_documents,
            documents,
        )

        return {
            "status": "started",
            "message": "Batch processing started.",
            "total": len(documents),
        }

    except Exception:
        if processing_lock.locked():
            processing_lock.release()

        raise


@router.post("/{document_id}")
def start_single_processing(
    document_id: str,
    background_tasks: BackgroundTasks,
):
    if not processing_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another processing job is already running.",
        )

    try:
        # Recover stale processing records before checking this document.
        recover_stale_documents(stale_after_minutes=30)

        document = get_document_for_processing(document_id)

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        status = document["processing_status"]

        if status == "failed":
            if not retry_failed_document(document_id):
                raise HTTPException(
                    status_code=409,
                    detail="Could not retry this document.",
                )

        elif status != "pending":
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Document cannot be processed from status: {status}"
                ),
            )

        initialize_processing_state(
            mode="single",
            total=1,
        )

        processing_state["current_document"] = {
            "document_id": document_id,
            "title": document["title"],
        }

        background_tasks.add_task(
            process_single_document,
            document_id,
            document["file_path"],
        )

        return {
            "status": "started",
            "message": "Document processing started.",
            "document_id": document_id,
        }

    except Exception:
        if processing_lock.locked():
            processing_lock.release()

        raise


@router.get("/status")
def get_processing_status():
    recovered_count = recover_stale_documents_if_idle()

    status = processing_state.copy()
    status["recovered_documents"] = recovered_count

    return status
