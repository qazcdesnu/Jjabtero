// @doc: docs/design/Citations.md#7-테스트

import { describe, expect, it, vi } from 'vitest'
import { DuplicatePaperError, type CitedWork, type PaperCitations } from './api'
import { citedWorkInput, createCitationListState } from './citationListState'

const work: CitedWork = {
  openalex_id: 'W10',
  title: 'Squeeze-and-Excitation Networks',
  authors: ['Jie Hu'],
  item_type: 'conference-paper',
  year: 2018,
  venue: 'CVPR',
  doi: '10.1109/cvpr.2018.00745',
  cited_by_count: 37192,
  shared_refs: 1,
  library_paper_id: null,
}

const data: PaperCitations = {
  state: 'ready',
  openalex_id: 'W1',
  fetched_at: null,
  window_start: '2017-06-12',
  window_end: '2018-06-12',
  citing_total: 592,
  citing_limit: 10,
  references: [],
  citations: [work],
}

function setup(overrides = {}) {
  const onAdded = vi.fn()
  const deps = {
    fetchPaperCitations: vi.fn().mockResolvedValue(structuredClone(data)),
    addPaper: vi.fn().mockResolvedValue({ id: 42 }),
    ...overrides,
  }
  return { lists: createCitationListState(onAdded, deps), deps, onAdded }
}

describe('citedWorkInput', () => {
  it('인용 논문을 서재 입력으로 바꾸고 OpenAlex ID를 넣는다', () => {
    expect(citedWorkInput(work)).toMatchObject({
      title: 'Squeeze-and-Excitation Networks',
      item_type: 'conference-paper',
      url: 'https://doi.org/10.1109/cvpr.2018.00745',
      openalex_id: 'W10',
      tags: [],
    })
    expect(citedWorkInput({ ...work, doi: null, title: null }).url).toBe('https://openalex.org/W10')
    expect(citedWorkInput({ ...work, title: null }).title).toBe('W10')
  })
})

describe('createCitationListState', () => {
  it('목록을 읽고, 담으면 서재에 있음으로 표시하고 알린다', async () => {
    const { lists, deps, onAdded } = setup()
    await lists.load(1)
    expect(deps.fetchPaperCitations).toHaveBeenCalledWith(1)
    await lists.add(lists.state.data!.citations[0])
    expect(deps.addPaper).toHaveBeenCalledWith(expect.objectContaining({ openalex_id: 'W10' }))
    expect(lists.state.data!.citations[0].library_paper_id).toBe(42)
    expect(onAdded).toHaveBeenCalled()
    expect(lists.state.adding).toEqual([])
  })

  it('이미 있는 DOI면 그 논문으로 표시하고, 다른 실패는 이유를 보여 준다', async () => {
    const duplicate = setup({ addPaper: vi.fn().mockRejectedValue(new DuplicatePaperError(7)) })
    await duplicate.lists.load(1)
    await duplicate.lists.add(duplicate.lists.state.data!.citations[0])
    expect(duplicate.lists.state.data!.citations[0].library_paper_id).toBe(7)

    const failing = setup({ addPaper: vi.fn().mockRejectedValue(new Error('서버 오류')) })
    await failing.lists.load(1)
    await failing.lists.add(failing.lists.state.data!.citations[0])
    expect(failing.lists.state.addErrors.W10).toBe('서버 오류')
  })

  it('다른 논문으로 바뀐 뒤 늦게 온 응답은 버린다', async () => {
    let resolveFirst: (value: PaperCitations) => void = () => undefined
    const fetchPaperCitations = vi
      .fn()
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce({ ...data, openalex_id: 'W2' })
    const { lists } = setup({ fetchPaperCitations })
    const first = lists.load(1)
    await lists.load(2)
    resolveFirst({ ...data, openalex_id: 'W1' })
    await first
    expect(lists.state.data!.openalex_id).toBe('W2')
  })
})
