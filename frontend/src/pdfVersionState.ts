// @doc: docs/design/PdfVersions.md#6-화면

import { computed, reactive } from 'vue'
import {
  fetchPdfVersion,
  listAvailablePdfVersions,
  listPdfVersions,
  selectPdfVersion,
  type AvailablePdfVersion,
  type SavedPdfVersion,
} from './api'

// 드롭다운의 항목 하나. value는 받은 판이면 `saved:<SHA-256>`, 받을 판이면 `fetch:<key>`다.
// @doc: docs/design/PdfVersions.md#6-화면
export interface VersionOption {
  value: string
  label: string
  detail: string
}

// @doc: docs/design/PdfVersions.md#6-화면
export interface VersionGroup {
  label: string
  items: VersionOption[]
}

function day(value: string): string {
  return value.slice(0, 10)
}

// @doc: docs/design/PdfVersions.md#6-화면
export function versionGroups(saved: SavedPdfVersion[], available: AvailablePdfVersion[]): VersionGroup[] {
  // 이미 받은 판은 받은 판 묶음에만 보이고, 받을 수 있는 판 목록에 있으면 그 이름(출처와 판 종류)을 쓴다.
  const names = new Map(available.flatMap((version) => (version.saved_sha256 ? [[version.saved_sha256, version.label]] : [])))
  const groups: VersionGroup[] = []
  if (saved.length)
    groups.push({
      label: '받은 판',
      items: saved.map((version) => ({
        value: `saved:${version.sha256}`,
        label: names.get(version.sha256) ?? version.label,
        detail: `${day(version.added_at)} 받음`,
      })),
    })
  const fresh = available.filter((version) => version.saved_sha256 === null)
  if (fresh.length)
    groups.push({
      label: '받을 수 있는 판',
      items: fresh.map((version) => ({
        value: `fetch:${version.key}`,
        label: version.label,
        detail: [version.date, version.latest ? '최신' : ''].filter(Boolean).join(' · '),
      })),
    })
  return groups
}

// @doc: docs/design/PdfVersions.md#6-화면
export function createPdfVersionState(
  paperId: () => number,
  onChanged: (sha256: string) => Promise<void> | void,
  deps = { listPdfVersions, listAvailablePdfVersions, fetchPdfVersion, selectPdfVersion },
) {
  // searched: 받을 수 있는 판을 이 논문에 대해 이미 찾았는지. 드롭다운을 열 때마다 바깥에 묻지 않기 위해서다.
  const state = reactive({
    saved: [] as SavedPdfVersion[],
    available: [] as AvailablePdfVersion[],
    searching: false,
    searched: false,
    busy: false,
    error: '',
    searchError: '',
  })
  const groups = computed(() => versionGroups(state.saved, state.available))
  const selected = computed(() => {
    const current = state.saved.find((version) => version.selected)
    return current ? `saved:${current.sha256}` : null
  })

  async function load(): Promise<void> {
    state.available = []
    state.searched = false
    state.error = ''
    state.searchError = ''
    try {
      state.saved = await deps.listPdfVersions(paperId())
    } catch (error) {
      state.saved = []
      state.error = error instanceof Error ? error.message : String(error)
    }
  }

  async function search(): Promise<void> {
    if (state.searched || state.searching) return
    state.searching = true
    state.searchError = ''
    try {
      state.available = await deps.listAvailablePdfVersions(paperId())
      state.searched = true
    } catch (error) {
      state.searchError = error instanceof Error ? error.message : String(error)
    } finally {
      state.searching = false
    }
  }

  async function choose(value: string): Promise<boolean> {
    if (value === selected.value || state.busy) return false
    state.busy = true
    state.error = ''
    const id = paperId()
    try {
      let sha256: string
      if (value.startsWith('saved:')) {
        sha256 = value.slice('saved:'.length)
        state.saved = await deps.selectPdfVersion(id, sha256)
      } else {
        sha256 = (await deps.fetchPdfVersion(id, value.slice('fetch:'.length))).sha256
        state.saved = await deps.listPdfVersions(id)
        state.available = state.available.map((version) =>
          `fetch:${version.key}` === value ? { ...version, saved_sha256: sha256 } : version,
        )
      }
      await onChanged(sha256)
      return true
    } catch (error) {
      state.error = error instanceof Error ? error.message : String(error)
      return false
    } finally {
      state.busy = false
    }
  }

  return { state, groups, selected, load, search, choose }
}
