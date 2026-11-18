// @doc: docs/design/PdfVersions.md#7-테스트

import { describe, expect, it, vi } from 'vitest'
import type { AvailablePdfVersion, SavedPdfVersion } from './api'
import { createPdfVersionState, versionGroups } from './pdfVersionState'

const A = 'a'.repeat(64)
const B = 'b'.repeat(64)

function saved(sha256: string, selected: boolean, label = 'arXiv v1'): SavedPdfVersion {
  return { sha256, label, source: 'arxiv', source_url: null, added_at: '2026-11-18T01:00:00', selected }
}

function available(key: string, saved_sha256: string | null = null): AvailablePdfVersion {
  return { key, label: key, url: `https://x/${key}`, date: '2026-03-12', latest: key === 'arxiv:v3', saved_sha256 }
}

function setup(overrides = {}) {
  const onChanged = vi.fn()
  const deps = {
    listPdfVersions: vi.fn().mockResolvedValue([saved(A, true)]),
    listAvailablePdfVersions: vi.fn().mockResolvedValue([available('arxiv:v3'), available('arxiv:v1', A)]),
    fetchPdfVersion: vi.fn().mockResolvedValue({ sha256: B }),
    selectPdfVersion: vi.fn().mockResolvedValue([saved(B, true), saved(A, false)]),
    ...overrides,
  }
  return { versions: createPdfVersionState(() => 3, onChanged, deps), deps, onChanged }
}

describe('versionGroups', () => {
  it('받은 판과, 아직 받지 않은 받을 수 있는 판을 묶는다', () => {
    expect(versionGroups([saved(A, true)], [available('arxiv:v3'), available('arxiv:v1', A)])).toEqual([
      { label: '받은 판', items: [{ value: `saved:${A}`, label: 'arxiv:v1', detail: '2026-11-18 받음' }] },
      { label: '받을 수 있는 판', items: [{ value: 'fetch:arxiv:v3', label: 'arxiv:v3', detail: '2026-03-12 · 최신' }] },
    ])
    expect(versionGroups([], [])).toEqual([])
    const named = versionGroups([saved(B, true, 's-rsa.com')], [{ ...available('url:x', B), label: 'SuperIntelligence · 출판판' }])
    expect(named[0]?.items[0]?.label).toBe('SuperIntelligence · 출판판')
  })
})

describe('createPdfVersionState', () => {
  it('받은 판을 불러와 지금 판을 고른 값으로 둔다', async () => {
    const { versions } = setup()
    await versions.load()
    expect(versions.selected.value).toBe(`saved:${A}`)
  })

  it('받을 수 있는 판은 한 번만 찾는다', async () => {
    const { versions, deps } = setup()
    await versions.search()
    await versions.search()
    expect(deps.listAvailablePdfVersions).toHaveBeenCalledTimes(1)
    expect(versions.groups.value.map((group) => group.items.length)).toEqual([1])
    await versions.load()
    expect(versions.state.searched).toBe(false)
  })

  it('받은 판을 고르면 지금 판으로 바꾸고 알린다. 지금 판을 다시 고르면 아무것도 하지 않는다', async () => {
    const { versions, deps, onChanged } = setup()
    await versions.load()
    await expect(versions.choose(`saved:${A}`)).resolves.toBe(false)
    await expect(versions.choose(`saved:${B}`)).resolves.toBe(true)
    expect(deps.selectPdfVersion).toHaveBeenCalledWith(3, B)
    expect(onChanged).toHaveBeenCalledWith(B)
    expect(versions.selected.value).toBe(`saved:${B}`)
  })

  it('받을 판을 고르면 받고, 받은 판을 다시 읽는다', async () => {
    const { versions, deps, onChanged } = setup()
    await versions.load()
    await versions.search()
    deps.listPdfVersions.mockResolvedValue([saved(B, true, 'arXiv v3'), saved(A, false)])
    await expect(versions.choose('fetch:arxiv:v3')).resolves.toBe(true)
    expect(deps.fetchPdfVersion).toHaveBeenCalledWith(3, 'arxiv:v3')
    expect(onChanged).toHaveBeenCalledWith(B)
    expect(versions.groups.value.map((group) => group.label)).toEqual(['받은 판'])
  })

  it('찾기와 받기 실패를 따로 알린다', async () => {
    const { versions } = setup({
      listAvailablePdfVersions: vi.fn().mockRejectedValue(new Error('502')),
      fetchPdfVersion: vi.fn().mockRejectedValue(new Error('PDF를 받지 못했습니다')),
    })
    await versions.search()
    expect(versions.state.searchError).toBe('502')
    await expect(versions.choose('fetch:arxiv:v3')).resolves.toBe(false)
    expect(versions.state.error).toBe('PDF를 받지 못했습니다')
    expect(versions.state.busy).toBe(false)
  })
})
