// @doc: docs/design/LibraryFilter.md#2-필터-조건

import type { Paper } from './api'

// @doc: docs/design/LibraryFilter.md#2-필터-조건
export interface LibraryFilter {
  text: string
  tags: string[]
  itemTypes: string[]
  yearFrom: number | null
  yearTo: number | null
}

// @doc: docs/design/LibraryFilter.md#2-필터-조건
export function emptyFilter(): LibraryFilter {
  return { text: '', tags: [], itemTypes: [], yearFrom: null, yearTo: null }
}

// @doc: docs/design/LibraryFilter.md#2-필터-조건
export function isFilterActive(filter: LibraryFilter): boolean {
  return (
    filter.text.trim() !== '' ||
    filter.tags.length > 0 ||
    filter.itemTypes.length > 0 ||
    filter.yearFrom !== null ||
    filter.yearTo !== null
  )
}

function haystack(paper: Paper): string {
  return [paper.title, ...paper.authors, paper.venue ?? '', paper.doi ?? '', ...paper.tags]
    .join('\n')
    .toLowerCase()
}

function matches(paper: Paper, filter: LibraryFilter, words: string[]): boolean {
  if (words.length > 0) {
    const text = haystack(paper)
    if (!words.every((word) => text.includes(word))) return false
  }
  if (!filter.tags.every((tag) => paper.tags.includes(tag))) return false
  if (filter.itemTypes.length > 0 && !filter.itemTypes.includes(paper.item_type)) return false
  if (filter.yearFrom !== null || filter.yearTo !== null) {
    if (paper.year === null) return false
    if (filter.yearFrom !== null && paper.year < filter.yearFrom) return false
    if (filter.yearTo !== null && paper.year > filter.yearTo) return false
  }
  return true
}

// @doc: docs/design/LibraryFilter.md#2-필터-조건
export function filterPapers(papers: Paper[], filter: LibraryFilter): Paper[] {
  const words = filter.text.trim().toLowerCase().split(/\s+/).filter((word) => word !== '')
  return papers.filter((paper) => matches(paper, filter, words))
}

// @doc: docs/design/LibraryFilter.md#2-필터-조건
export function tagCounts(papers: Paper[]): { name: string; count: number }[] {
  const counts = new Map<string, number>()
  for (const paper of papers) {
    for (const tag of paper.tags) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1)
    }
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name))
}
