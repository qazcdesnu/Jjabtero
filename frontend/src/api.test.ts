// @doc: docs/design/AppSkeleton.md#4-테스트
// @doc: docs/design/PaperSearch.md#5-테스트
// @doc: docs/design/LibraryView.md#4-테스트
// @doc: docs/design/ReadingStatus.md#4-테스트
// @doc: docs/design/DriveSync.md#8-테스트

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DuplicatePaperError,
  PaperNotFoundError,
  addPaper,
  deletePaper,
  disconnectDrive,
  driveConnectUrl,
  fetchDriveStatus,
  resolveDrive,
  syncDrive,
  listPapers,
  fetchHealth,
  searchPapers,
  toPaperInput,
  updateReading,
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
  const input = toPaperInput(result, [])

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
  it('검색 결과를 입력으로 바꾸고 태그의 공백·빈 값·중복을 정리한다', () => {
    expect(toPaperInput(result, [' nlp', ' ', 'transformer ', 'nlp'])).toEqual({
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

describe('listPapers', () => {
  it('서재 목록을 돌려준다', async () => {
    const papers = [{ id: 1, title: 'A' }]
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(papers)))
    vi.stubGlobal('fetch', fetchMock)

    await expect(listPapers()).resolves.toEqual(papers)
    expect(fetchMock).toHaveBeenCalledWith('/api/papers')
  })

  it('실패 응답이면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))

    await expect(listPapers()).rejects.toThrow('500')
  })
})

describe('deletePaper', () => {
  it('204면 끝난다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(deletePaper(3)).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('/api/papers/3', { method: 'DELETE' })
  })

  it('404면 PaperNotFoundError를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))

    await expect(deletePaper(3)).rejects.toBeInstanceOf(PaperNotFoundError)
  })

  it('그 밖의 실패면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))

    await expect(deletePaper(3)).rejects.toThrow('500')
  })
})

describe('updateReading', () => {
  it('보낸 항목을 PATCH로 보내고 바뀐 논문을 돌려준다', async () => {
    const changed = { id: 3, read_status: 'read' }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(changed)))
    vi.stubGlobal('fetch', fetchMock)

    await expect(updateReading(3, { read_status: 'read' })).resolves.toEqual(changed)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/papers/3',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ read_status: 'read' }) }),
    )
  })

  it('404면 PaperNotFoundError를, 그 밖의 실패면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))
    await expect(updateReading(3, { note: 'x' })).rejects.toBeInstanceOf(PaperNotFoundError)

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    await expect(updateReading(3, { note: 'x' })).rejects.toThrow('500')
  })
})

describe('드라이브 API', () => {
  const ok = { state: 'idle', message: '', last_synced_at: null, pending: false, data_version: 0 }

  it('상태, 동기화, 충돌 풀기, 연결 해제를 부른다', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify(ok)))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchDriveStatus()).resolves.toEqual(ok)
    await syncDrive()
    await resolveDrive('remote')
    await disconnectDrive()
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/drive/status',
      '/api/drive/sync',
      '/api/drive/resolve',
      '/api/drive/disconnect',
    ])
    expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: 'POST', body: JSON.stringify({ choice: 'remote' }) })
  })

  it('실패 응답이면 상태 코드를 담은 오류를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    await expect(syncDrive()).rejects.toThrow('500')
  })

  it('연결 주소에 돌아올 주소를 담는다', () => {
    expect(driveConnectUrl('http://localhost:5173/')).toBe(
      '/api/drive/connect?return_to=http%3A%2F%2Flocalhost%3A5173%2F',
    )
  })
})

