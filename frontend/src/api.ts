// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱

// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
export interface Health {
  status: string
  version: string
}

// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
export async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new Error(`서버 상태 확인 실패: ${response.status}`)
  }
  return (await response.json()) as Health
}
