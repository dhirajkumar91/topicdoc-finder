import API_BASE_URL from "./api"

export async function searchKnowledgeBase(query) {
  const response = await fetch(`${API_BASE_URL}/api/search/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  })

  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`)
  }

  return response.json()
}