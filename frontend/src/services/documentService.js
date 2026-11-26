
import API_BASE_URL from "./api"

// Fetch registered documents.
export async function getDocuments(limit = 20, offset = 0) {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/?limit=${limit}&offset=${offset}`
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.status}`)
  }

  return response.json()
}

// Start processing or retry a single document.
export async function startSingleProcessing(documentId) {
  const response = await fetch(
    `${API_BASE_URL}/api/processing/${documentId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to start document processing.')
  }

  return data
}

// Start batch processing of pending documents.
export async function startBatchProcessing(limit = 3) {
  const response = await fetch(
    `${API_BASE_URL}/api/processing/batch`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ limit }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to start batch processing.')
  }

  return data
}

// Get current processing job status.
export async function getProcessingStatus() {
  const response = await fetch(
    `${API_BASE_URL}/api/processing/status`
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch processing status: ${response.status}`)
  }

  return response.json()
}
