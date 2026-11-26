
import time


from embeddings.embedding_service import (
    generate_document_embedding,
)


def generate_embeddings_in_batches(
    chunks,
    batch_size=10,
    max_retries=3,
    retry_delay=2,
    progress_callback=None,
):
    """
    Generate embeddings for multiple document chunks.

    Each successful result retains its original chunk metadata.

    Failed chunks are recorded separately.

    Optional progress_callback receives:
        completed_chunks
        total_chunks
        successful_chunks
        failed_chunks
        current_batch
        total_batches
    """

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero.")

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative.")

    results = []
    failures = []

    total_chunks = len(chunks)
    completed_chunks = 0

    if total_chunks == 0:
        return {
            "results": results,
            "failures": failures,
        }

    total_batches = (
        total_chunks + batch_size - 1
    ) // batch_size

    def report_progress(current_batch):
        """
        Report progress without interrupting embedding generation.
        """

        if progress_callback is None:
            return

        try:
            progress_callback({
                "completed_chunks": completed_chunks,
                "total_chunks": total_chunks,
                "successful_chunks": len(results),
                "failed_chunks": len(failures),
                "current_batch": current_batch,
                "total_batches": total_batches,
            })

        except Exception as error:
            print(f"Progress reporting failed: {error}")

    report_progress(0)

    for batch_number, start in enumerate(
        range(0, total_chunks, batch_size),
        start=1,
    ):

        batch = chunks[start:start + batch_size]

        print(
            f"\nProcessing batch {batch_number}/{total_batches} "
            f"({len(batch)} chunks)"
        )

        for chunk in batch:

            chunk_id = chunk["chunk_index"]

            for attempt in range(max_retries + 1):

                try:

                    embedding = generate_document_embedding(
                        text=chunk["content"],
                        title=chunk["section_title"],
                    )

                    results.append({
                        **chunk,
                        "embedding": embedding,
                    })

                    print(
                        f"  Chunk {chunk_id}: embedding generated"
                    )

                    break

                except Exception as error:

                    if attempt < max_retries:

                        delay = retry_delay * (2 ** attempt)

                        print(
                            f"  Chunk {chunk_id}: attempt "
                            f"{attempt + 1} failed: {error}"
                        )

                        print(
                            f"  Retrying in {delay} seconds..."
                        )

                        time.sleep(delay)

                    else:

                        print(
                            f"  Chunk {chunk_id}: failed after "
                            f"{max_retries + 1} attempts."
                        )

                        failures.append({
                            "chunk_index": chunk_id,
                            "error": str(error),
                        })

            # A chunk is counted after it succeeds or exhausts retries.
            completed_chunks += 1

            report_progress(batch_number)

    return {
        "results": results,
        "failures": failures,
    }




def generate_table_embeddings_in_batches(
    tables,
    batch_size=10,
    max_retries=3,
    retry_delay=2,
    progress_callback=None,
):
    """
    Generate embeddings for extracted PDF tables.

    Reuses the existing batch embedding implementation while
    preserving the original table metadata.

    Returns:
        {
            "results": [...],
            "failures": [...]
        }
    """

    if not tables:
        return {
            "results": [],
            "failures": [],
        }

    table_inputs = []

    for table in tables:
        table_index = table["table_index"]

        table_title = (
            table.get("table_title")
            or table.get("section_title")
            or "Untitled table"
        )

        table_inputs.append({
            **table,
            "_original_section_title": table.get("section_title"),
            "chunk_index": table_index,
            "content": table["table_text"],
            "section_title": table_title,
        })

    batch_result = generate_embeddings_in_batches(
        chunks=table_inputs,
        batch_size=batch_size,
        max_retries=max_retries,
        retry_delay=retry_delay,
        progress_callback=progress_callback,
    )

    # Remove temporary chunk-specific fields.
    results = []

    for result in batch_result["results"]:
        table_result = {
            key: value
            for key, value in result.items()
            if key not in (
                "chunk_index",
                "content",
                "_original_section_title",
            )
        }

        table_result["section_title"] = result["_original_section_title"]

        results.append(table_result)
    failures = [
        {
            "table_index": failure["chunk_index"],
            "error": failure["error"],
        }
        for failure in batch_result["failures"]
    ]

    return {
        "results": results,
        "failures": failures,
    }
