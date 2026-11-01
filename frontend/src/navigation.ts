// @doc: docs/design/UiLayout.md#3-화면-배치

// @doc: docs/design/UiLayout.md#3-화면-배치
export const VIEWS = [
  { name: 'library', label: '서재', icon: 'pi pi-book' },
  { name: 'search', label: '논문 검색', icon: 'pi pi-search' },
] as const

// @doc: docs/design/UiLayout.md#3-화면-배치
export const DEFAULT_VIEW: (typeof VIEWS)[number]['name'] = 'search'
