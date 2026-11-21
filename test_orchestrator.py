from unittest.mock import patch

from process_pending_documents import process_pending_documents


def test_orchestrator():

    test_documents = [
        {
            "document_id": "test1",
            "file_path": "file1.pdf",
            "original_filename": "file1.pdf",
        },
        {
            "document_id": "test2",
            "file_path": "file2.pdf",
            "original_filename": "file2.pdf",
        },
        {
            "document_id": "test3",
            "file_path": "file3.pdf",
            "original_filename": "file3.pdf",
        },
        {
            "document_id": "test4",
            "file_path": "file4.pdf",
            "original_filename": "file4.pdf",
        },
    ]

    execution_order = []

    def mock_recovery(stale_after_minutes=30):
        execution_order.append("recovery")

        assert stale_after_minutes == 30

        return 1

    def mock_get_pending_documents(limit=10):
        execution_order.append("fetch_pending")

        assert limit == 10

        return test_documents

    def mock_process_document(document_id, file_path):

        execution_order.append(f"process_{document_id}")

        if document_id == "test1":
            return {
                "document_id": document_id,
                "status": "completed",
                "chunk_count": 10,
            }

        elif document_id == "test2":
            raise Exception("Simulated processing failure")

        elif document_id == "test3":
            return {
                "document_id": document_id,
                "status": "skipped",
                "chunk_count": 0,
            }

        elif document_id == "test4":
            return {
                "document_id": document_id,
                "status": "completed",
                "chunk_count": 15,
            }

    with patch(
        "process_pending_documents.recover_stale_documents",
        side_effect=mock_recovery,
    ), patch(
        "process_pending_documents.get_pending_documents",
        side_effect=mock_get_pending_documents,
    ), patch(
        "process_pending_documents.process_document",
        side_effect=mock_process_document,
    ):

        result = process_pending_documents(limit=10)

    # Verify execution order.
    expected_order = [
        "recovery",
        "fetch_pending",
        "process_test1",
        "process_test2",
        "process_test3",
        "process_test4",
    ]

    assert execution_order == expected_order, (
        f"Unexpected execution order: {execution_order}"
    )

    # Verify processing statistics.
    assert result["total"] == 4
    assert result["completed"] == 2
    assert result["failed"] == 1
    assert result["skipped"] == 1

    print("\nExecution order verification passed!")
    print("Processing statistics verification passed!")
    print(f"Test result: {result}")


if __name__ == "__main__":
    test_orchestrator()