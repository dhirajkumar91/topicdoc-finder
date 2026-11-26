
import API_BASE_URL from "./api"

export async function discoverResearch(query, maxResultsPerSource = 5) {
  const response = await fetch(`${API_BASE_URL}/api/discovery/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      max_results_per_source: maxResultsPerSource,
    }),
  })

  if (!response.ok) {
    throw new Error(`Discovery failed: ${response.status}`)
  }

  return response.json()
}

export async function downloadSelectedPapers(papers) {
  const response = await fetch(`${API_BASE_URL}/api/downloads/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ papers }),
  })

  if (!response.ok) {
    throw new Error(`Download request failed: ${response.status}`)
  }

  return response.json()
}

export async function uploadManualPdf(file, paper) {
  const formData = new FormData()

  formData.append('file', file)
  formData.append('metadata', JSON.stringify(paper))

  const response = await fetch(`${API_BASE_URL}/api/downloads/manual`, {
    method: 'POST',
    body: formData,
  })

  const result = await response.json()

  if (!response.ok) {
    throw new Error(
      result.detail || `Manual PDF upload failed: ${response.status}`
    )
  }

  return result
}
