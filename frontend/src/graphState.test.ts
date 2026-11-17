// @doc: docs/design/CitationGraph.md#5-테스트
// @doc: docs/design/Tags.md#6-테스트

import { describe, expect, it, vi } from 'vitest'
import { DuplicatePaperError, type CitationGraph, type GraphNode } from './api'
import { OUTSIDE_COUNT, createGraphState } from './graphState'

const outside: GraphNode = {
  id: 'W9',
  paper_id: null,
  openalex_id: 'W9',
  title: 'Outside',
  item_type: 'article',
  authors: ['Lee'],
  year: 2019,
  venue: null,
  doi: '10.1/w9',
  cited_by_count: 10,
  has_data: true,
  score: 1.2,
}
const before: CitationGraph = { nodes: [outside], edges: [] }
const after: CitationGraph = { nodes: [{ ...outside, id: 'p5', paper_id: 5, score: null }], edges: [] }

function setup(overrides = {}) {
  const onAdded = vi.fn()
  const deps = {
    fetchCitationGraph: vi.fn().mockResolvedValueOnce(before).mockResolvedValue(after),
    addPaper: vi.fn().mockResolvedValue({ id: 5 }),
    ...overrides,
  }
  return { graph: createGraphState(onAdded, deps), deps, onAdded }
}

describe('createGraphState', () => {
  it('추천 논문 함께 보기를 켜면 그 수만큼 청해 읽고, 점을 고른다', async () => {
    const { graph, deps } = setup()
    await graph.load()
    expect(deps.fetchCitationGraph).toHaveBeenLastCalledWith(0, [])
    graph.state.outside = true
    await graph.load()
    expect(deps.fetchCitationGraph).toHaveBeenLastCalledWith(OUTSIDE_COUNT, [])
    graph.state.data = before
    graph.select('W9')
    expect(graph.selected.value?.title).toBe('Outside')
  })

  it('서재 밖 논문을 담으면 서재를 다시 읽게 하고, 그래프를 다시 읽어 서재 점을 고른다', async () => {
    const { graph, deps, onAdded } = setup()
    await graph.load()
    graph.select('W9')
    await graph.add(outside)
    expect(deps.addPaper).toHaveBeenCalledWith(expect.objectContaining({ openalex_id: 'W9', doi: '10.1/w9', title: 'Outside' }))
    expect(onAdded).toHaveBeenCalled()
    expect(graph.state.selectedId).toBe('p5')
  })

  it('이미 있으면 다시 읽기만 하고, 다른 실패는 이유를, 읽기 실패는 오류를 보여 준다', async () => {
    const duplicate = setup({ addPaper: vi.fn().mockRejectedValue(new DuplicatePaperError(5)) })
    await duplicate.graph.load()
    await duplicate.graph.add(outside)
    expect(duplicate.graph.state.selectedId).toBe('p5')

    const failing = setup({ addPaper: vi.fn().mockRejectedValue(new Error('서버 오류')) })
    await failing.graph.add(outside)
    expect(failing.graph.state.addError).toBe('서버 오류')
    expect(failing.graph.state.adding).toBe(false)

    const broken = setup({ fetchCitationGraph: vi.fn().mockRejectedValue(new Error('인용 그래프 불러오기 실패: 500')) })
    await broken.graph.load()
    expect(broken.graph.state.error).toContain('500')
  })

  it('고른 태그로 그래프를 청한다', async () => {
    const tags = ['nlp']
    const deps = { fetchCitationGraph: vi.fn().mockResolvedValue(before), addPaper: vi.fn() }
    const graph = createGraphState(vi.fn(), deps, () => tags)
    await graph.load()
    expect(deps.fetchCitationGraph).toHaveBeenLastCalledWith(0, ['nlp'])
    tags.push('core')
    await graph.load()
    expect(deps.fetchCitationGraph).toHaveBeenLastCalledWith(0, ['nlp', 'core'])
  })
})
