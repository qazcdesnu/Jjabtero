// @doc: docs/design/AppSkeleton.md#4-테스트
// @doc: docs/design/PaperSearch.md#5-테스트

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DuplicatePaperError,
  addPaper,
  fetchHealth,
  searchPapers,
  toPaperInput,
  type SearchResult,
} from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchHealth', () => {
  it('성공 응답이면 상태를 돌려준다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', version: '0.1.0' }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchHealth()).resolves.toEqual({ status: 'ok', version: '0.1.0' })
    expect(fetchMock).toHaveBeenCalledWith('/api/health')
  })

  it('실패 응답이면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })))

    await expect(fetchHealth()).rejects.toThrow('503')
  })
})

const result: SearchResult = {
  source: 'openalex',
  source_id: 'W1',
  title: 'Attention Is All You Need',
  authors: ['Ashish Vaswani'],
  item_type: 'preprint',
  year: 2017,
  venue: 'arXiv',
  doi: '10.48550/arxiv.1706.03762',
  url: 'https://arxiv.org/abs/1706.03762',
  library_paper_id: null,
}

describe('searchPapers', () => {
  it('검색어와 검색원을 질의로 보내고 응답을 돌려준다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ results: [result], errors: [] })))
    vi.stubGlobal('fetch', fetchMock)

    await expect(searchPapers('attention need', ['openalex', 'arxiv'])).resolves.toEqual({
      results: [result],
      errors: [],
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/search?q=attention+need&sources=openalex&sources=arxiv',
    )
  })

  it('실패 응답이면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 422 })))

    await expect(searchPapers('x', ['openalex'])).rejects.toThrow('422')
  })
})

describe('addPaper', () => {
  const input = toPaperInput(result, '')

  it('성공하면 저장된 논문을 돌려준다', async () => {
    const paper = { ...input, id: 1, created_at: 'now', updated_at: 'now' }
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(paper), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(addPaper(input)).resolves.toEqual(paper)
    expect(fetchMock).toHaveBeenCalledWith('/api/papers', expect.objectContaining({ method: 'POST' }))
  })

  it('409면 이미 있는 논문 ID를 담은 DuplicatePaperError를 던진다', async () => {
    const body = { detail: { message: 'dup', paper_id: 7 } }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 409 })),
    )

    const error = await addPaper(input).catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(DuplicatePaperError)
    expect((error as DuplicatePaperError).paperId).toBe(7)
  })

  it('그 밖의 실패면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))

    await expect(addPaper(input)).rejects.toThrow('500')
  })
})

describe('toPaperInput', () => {
  it('검색 결과를 입력으로 바꾸고 쉼표로 나눈 태그의 빈 칸을 버린다', () => {
    expect(toPaperInput(result, ' nlp, ,transformer ,')).toEqual({
      title: 'Attention Is All You Need',
      authors: ['Ashish Vaswani'],
      item_type: 'preprint',
      year: 2017,
      venue: 'arXiv',
      doi: '10.48550/arxiv.1706.03762',
      url: 'https://arxiv.org/abs/1706.03762',
      tags: ['nlp', 'transformer'],
    })
  })
})
