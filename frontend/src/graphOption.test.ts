// @doc: docs/design/CitationGraph.md#5-테스트

import { describe, expect, it } from 'vitest'
import type { CitationGraph, GraphNode } from './api'
import { dateLabel, edgeText, graphOption, orderWithinYear, symbolSize, yearLayout } from './graphOption'

function node(id: string, year: number | null, extra: Partial<GraphNode> = {}): GraphNode {
  return {
    id,
    paper_id: id.startsWith('p') ? Number(id.slice(1)) : null,
    openalex_id: null,
    title: `Title ${id}`,
    item_type: 'article',
    authors: [],
    year,
    venue: null,
    doi: null,
    cited_by_count: null,
    date: null,
    date_precision: year === null ? null : 'year',
    has_data: true,
    score: id.startsWith('p') ? null : 1,
    ...extra,
  }
}

const graph: CitationGraph = {
  nodes: [node('p1', 2017), node('p2', 2018), node('W9', 2017, { cited_by_count: 500 }), node('p3', null, { has_data: false })],
  edges: [
    { source: 'p2', target: 'p1', kind: 'cites', shared_refs: 0, cocited: 0 },
    { source: 'p1', target: 'W9', kind: 'related', shared_refs: 2, cocited: 3 },
    { source: 'p3', target: 'p1', kind: 'cites', shared_refs: 0, cocited: 0 },
  ],
}
const palette = { library: '#0f0', outside: '#888', text: '#000', edge: '#999' }

type Series = { layout: string; data: { id: string; value?: number[]; category: number; label: { show: boolean } }[]; links: { source: string; symbol: string[]; lineStyle: { type: string } }[] }

describe('yearLayout', () => {
  it('점이 있는 연도만 열로 두고, 서재 논문을 위로 쌓으며, 연도를 모르는 점은 뺀다', () => {
    const { years, positions, hidden } = yearLayout([...graph.nodes, node('W8', 1997)])
    expect(years).toEqual([1997, 2017, 2018])
    expect(positions.get('W8')).toEqual([0, 0])
    expect(positions.get('p1')).toEqual([1, 0])
    expect(positions.get('W9')).toEqual([1, 1])
    expect(positions.get('p2')).toEqual([2, 0])
    expect(positions.has('p3')).toBe(false)
    expect(hidden).toBe(1)
  })
})

describe('graphOption', () => {
  it('연도 순은 좌표축 위에 두고, 빠진 점에 닿는 선도 뺀다', () => {
    const option = graphOption(graph, 'year', palette) as { series: Series[]; xAxis: { type: string; data: string[] } }
    const series = option.series[0]
    expect(series.layout).toBe('none')
    expect(series.data.map((item) => item.id)).toEqual(['p1', 'p2', 'W9'])
    expect(series.links).toHaveLength(2)
    expect(option.xAxis).toMatchObject({ type: 'category', data: ['2017', '2018'] })
  })

  it('자유 배치는 모든 점을 힘 배치로 그리고, 점과 선의 모양을 종류에 맞춘다', () => {
    const option = graphOption(graph, 'force', palette) as { series: Series[]; xAxis?: unknown }
    const series = option.series[0]
    expect(series.layout).toBe('force')
    expect(option.xAxis).toBeUndefined()
    expect(series.data).toHaveLength(4)
    const w9 = series.data.find((item) => item.id === 'W9')!
    expect(w9.label.show).toBe(false)
    expect(w9.category).toBe(1)
    const [cites, related] = series.links
    expect([cites.symbol, cites.lineStyle.type]).toEqual([['none', 'arrow'], 'solid'])
    expect([related.symbol, related.lineStyle.type]).toEqual([['none', 'none'], 'dashed'])
  })

  it('점 크기는 피인용 수에 따라 커지고, 선 설명은 관계를 말한다', () => {
    expect(symbolSize(node('a', 1))).toBe(12)
    expect(symbolSize(node('a', 1, { cited_by_count: 100000 }))).toBeGreaterThan(symbolSize(node('a', 1, { cited_by_count: 10 })))
    const names = new Map([['p1', 'A'], ['W9', 'B']])
    expect(edgeText(graph.edges[1], names)).toBe('A ↔ B: 공유 참고문헌 2, 함께 인용 3회')
    expect(edgeText({ ...graph.edges[0], source: 'W9', target: 'p1' }, names)).toBe('B → A 인용')
  })
})

describe('orderWithinYear', () => {
  const day = (id: string, date: string, extra: Partial<GraphNode> = {}) =>
    node(id, 2017, { date, date_precision: 'day', ...extra })

  it('같은 연도 안에서는 공개일이 이른 논문을 위에, 월까지만 알면 그달 가운데로, 연도만 알면 아래에 둔다', () => {
    const nodes = [
      day('p1', '2017-12-06'),
      node('p2', 2017),
      node('W3', 2017, { date: '2017-06', date_precision: 'month' }),
      day('p4', '2017-06-12'),
      day('p5', '2017-06-20'),
    ]
    expect(orderWithinYear(nodes, []).map((item) => item.id)).toEqual(['p4', 'W3', 'p5', 'p1', 'p2'])
  })

  it('같은 연도의 인용 관계는 날짜보다 앞서 인용된 논문을 위에 두고, 날짜를 모르는 논문도 인용 관계로 자리를 정한다', () => {
    const nodes = [day('p1', '2017-03-01'), day('p2', '2017-09-01'), node('p3', 2017)]
    const edges = [
      // p1이 p2를 인용한다: 날짜는 p1이 이르지만(판 차이) 인용된 p2가 위다.
      { source: 'p1', target: 'p2', kind: 'cites' as const, shared_refs: 0, cocited: 0 },
      // p2가 날짜를 모르는 p3을 인용한다: p3이 p2보다 위다.
      { source: 'p2', target: 'p3', kind: 'cites' as const, shared_refs: 0, cocited: 0 },
    ]
    expect(orderWithinYear(nodes, edges).map((item) => item.id)).toEqual(['p3', 'p2', 'p1'])
  })

  it('서로 인용해 순서가 돌면 날짜로 끊는다', () => {
    const nodes = [day('p1', '2017-09-01'), day('p2', '2017-03-01')]
    const edges = [
      { source: 'p1', target: 'p2', kind: 'cites' as const, shared_refs: 0, cocited: 0 },
      { source: 'p2', target: 'p1', kind: 'cites' as const, shared_refs: 0, cocited: 0 },
    ]
    expect(orderWithinYear(nodes, edges).map((item) => item.id)).toEqual(['p2', 'p1'])
  })

  it('날짜 표시는 정밀도를 함께 보인다', () => {
    expect(dateLabel(day('a', '2017-06-12'))).toBe('2017-06-12')
    expect(dateLabel(node('a', 2018, { date: '2018-03', date_precision: 'month' }))).toBe('2018-03 (월까지)')
    expect(dateLabel(node('a', 2018))).toBe('2018 (연도만)')
    expect(dateLabel(node('a', null))).toBe('연도 모름')
  })

  it('같은 연도에 다른 논문이 있는데 연도만 아는 논문 수를 센다', () => {
    const { undated } = yearLayout([day('p1', '2017-01-05'), node('p2', 2017), node('p3', 2016)])
    expect(undated).toBe(1)
  })
})

