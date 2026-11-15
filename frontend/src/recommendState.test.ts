// @doc: docs/design/Citations.md#7-테스트

import { describe, expect, it, vi } from 'vitest'
import { DuplicatePaperError, type RecommendedWork } from './api'
import { createRecommendState } from './recommendState'

const work: RecommendedWork = {
  openalex_id: 'W10',
  title: 'Graph Attention Networks',
  authors: ['Petar Veličković'],
  item_type: 'preprint',
  year: 2017,
  venue: 'arXiv',
  doi: null,
  cited_by_count: 20398,
  shared_refs: null,
  library_paper_id: null,
  score: 1.6,
  sources: [{ paper_id: 1, title: 'Attention Is All You Need', direction: 'later', direction_basis: 'citation' }],
  direction: 'later',
}

function setup(overrides = {}) {
  const onAdded = vi.fn()
  const deps = {
    fetchRecommendations: vi.fn().mockResolvedValue({ papers: 2, papers_used: 1, works: [work] }),
    addPaper: vi.fn().mockResolvedValue({ id: 5 }),
    ...overrides,
  }
  return { recommend: createRecommendState(onAdded, deps), deps, onAdded }
}

describe('createRecommendState', () => {
  it('추천을 읽고, 담으면 담음으로 표시하고 서재를 다시 읽게 한다', async () => {
    const { recommend, deps, onAdded } = setup()
    await recommend.load()
    expect(recommend.state.data!.works).toHaveLength(1)
    await recommend.add(work)
    expect(deps.addPaper).toHaveBeenCalledWith(expect.objectContaining({ openalex_id: 'W10', url: 'https://openalex.org/W10' }))
    expect(recommend.state.added).toEqual(['W10'])
    expect(onAdded).toHaveBeenCalled()
  })

  it('이미 있으면 담음으로, 다른 실패는 이유를, 읽기 실패는 오류를 보여 준다', async () => {
    const duplicate = setup({ addPaper: vi.fn().mockRejectedValue(new DuplicatePaperError(3)) })
    await duplicate.recommend.add(work)
    expect(duplicate.recommend.state.added).toEqual(['W10'])

    const failing = setup({ addPaper: vi.fn().mockRejectedValue(new Error('서버 오류')) })
    await failing.recommend.add(work)
    expect(failing.recommend.state.addErrors.W10).toBe('서버 오류')

    const broken = setup({ fetchRecommendations: vi.fn().mockRejectedValue(new Error('추천 불러오기 실패: 500')) })
    await broken.recommend.load()
    expect(broken.recommend.state.error).toContain('500')
    expect(broken.recommend.state.loading).toBe(false)
  })
})
