// @doc: docs/design/CitationGraph.md#4-화면

import type { EChartsCoreOption } from 'echarts/core'
import type { CitationGraph, GraphEdge, GraphNode } from './api'

// @doc: docs/design/CitationGraph.md#4-화면
export type GraphLayout = 'year' | 'force'

// @doc: docs/design/CitationGraph.md#4-화면
export interface GraphPalette {
  library: string
  outside: string
  text: string
  edge: string
}

// 같은 연도 안에서 견줄 날짜. 월까지만 알면 그달 가운데로 본다. 연도만 알면 견줄 수 없다(null).
function dateKey(node: GraphNode): string | null {
  if (node.date_precision === 'day' && node.date) return node.date
  if (node.date_precision === 'month' && node.date) return `${node.date}-15`
  return null
}

function earlier(a: GraphNode, b: GraphNode): number {
  const left = dateKey(a)
  const right = dateKey(b)
  if (left !== null && right !== null && left !== right) return left < right ? -1 : 1
  // 날짜를 아는 논문을 모르는 논문보다 위에 둔다.
  if ((left === null) !== (right === null)) return left === null ? 1 : -1
  return (
    Number(a.paper_id === null) - Number(b.paper_id === null) ||
    (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0) ||
    a.id.localeCompare(b.id)
  )
}

// @doc: docs/design/CitationGraph.md#4-화면
export function orderWithinYear(group: GraphNode[], edges: GraphEdge[]): GraphNode[] {
  // 인용 관계가 있으면 인용된 논문(선행)을 위에 둔다. 그 밖에는 날짜순이다(위상 정렬, 같은 차례면 날짜).
  const ids = new Set(group.map((node) => node.id))
  const before = new Map(group.map((node) => [node.id, new Set<string>()]))
  for (const edge of edges) {
    if (edge.kind === 'cites' && ids.has(edge.source) && ids.has(edge.target) && edge.source !== edge.target) {
      before.get(edge.source)!.add(edge.target)
    }
  }
  const remaining = [...group]
  const placed = new Set<string>()
  const ordered: GraphNode[] = []
  while (remaining.length) {
    const ready = remaining.filter((node) => [...before.get(node.id)!].every((id) => placed.has(id)))
    // 서로 인용해 순서가 돌면 날짜로 끊는다.
    const pool = ready.length ? ready : remaining
    const next = pool.reduce((best, node) => (earlier(node, best) < 0 ? node : best))
    ordered.push(next)
    placed.add(next.id)
    remaining.splice(remaining.indexOf(next), 1)
  }
  return ordered
}

// @doc: docs/design/CitationGraph.md#4-화면
export function yearLayout(
  nodes: GraphNode[],
  edges: GraphEdge[] = [],
): {
  years: number[]
  positions: Map<string, [number, number]>
  hidden: number
  undated: number
} {
  const byYear = new Map<number, GraphNode[]>()
  let hidden = 0
  for (const node of nodes) {
    if (node.year === null) {
      hidden += 1
      continue
    }
    byYear.set(node.year, [...(byYear.get(node.year) ?? []), node])
  }
  // 점이 없는 연도는 건너뛴다. 오래된 논문 하나 때문에 축이 길게 늘어나지 않게 하기 위해서다.
  const years = [...byYear.keys()].sort((a, b) => a - b)
  const positions = new Map<string, [number, number]>()
  let undated = 0
  years.forEach((year, column) => {
    const group = byYear.get(year)!
    // 혼자인 연도는 순서를 따질 필요가 없다.
    if (group.length > 1) undated += group.filter((node) => dateKey(node) === null).length
    orderWithinYear(group, edges).forEach((node, index) => positions.set(node.id, [column, index]))
  })
  return { years, positions, hidden, undated }
}

// @doc: docs/design/CitationGraph.md#4-화면
export function dateLabel(node: GraphNode): string {
  if (node.date_precision === 'day' && node.date) return node.date
  if (node.date_precision === 'month' && node.date) return `${node.date} (월까지)`
  return node.year ? `${node.year} (연도만)` : '연도 모름'
}

// @doc: docs/design/CitationGraph.md#4-화면
export function symbolSize(node: GraphNode): number {
  if (node.cited_by_count === null) return 12
  return Math.min(36, 8 + 4 * Math.log10(1 + node.cited_by_count))
}

function shortTitle(title: string): string {
  return title.length > 28 ? `${title.slice(0, 27)}…` : title
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`)
}

// @doc: docs/design/CitationGraph.md#4-화면
export function edgeText(edge: GraphEdge, names: Map<string, string>): string {
  const source = names.get(edge.source) ?? edge.source
  const target = names.get(edge.target) ?? edge.target
  if (edge.kind === 'cites') return `${source} → ${target} 인용`
  const parts = []
  if (edge.shared_refs) parts.push(`공유 참고문헌 ${edge.shared_refs}`)
  if (edge.cocited) parts.push(`함께 인용 ${edge.cocited}회`)
  return `${source} ↔ ${target}: ${parts.join(', ') || '가까움'}`
}

// @doc: docs/design/CitationGraph.md#4-화면
export function graphOption(graph: CitationGraph, layout: GraphLayout, palette: GraphPalette): EChartsCoreOption {
  const year = layout === 'year' ? yearLayout(graph.nodes, graph.edges) : null
  const placed = year ? year.positions : null
  const nodes = placed ? graph.nodes.filter((node) => placed.has(node.id)) : graph.nodes
  const shown = new Set(nodes.map((node) => node.id))
  const edges = graph.edges.filter((edge) => shown.has(edge.source) && shown.has(edge.target))
  const names = new Map(graph.nodes.map((node) => [node.id, shortTitle(node.title)]))
  const byId = new Map(graph.nodes.map((node) => [node.id, node]))
  const stack = placed ? Math.max(0, ...[...placed.values()].map(([, y]) => y)) : 0

  const data = nodes.map((node) => {
    const library = node.paper_id !== null
    return {
      id: node.id,
      name: node.title,
      value: placed ? placed.get(node.id) : undefined,
      category: library ? 0 : 1,
      symbolSize: symbolSize(node),
      itemStyle: { opacity: library && !node.has_data ? 0.35 : 1 },
      label: { show: library, formatter: shortTitle(node.title) },
    }
  })
  const links = edges.map((edge) => ({
    source: edge.source,
    target: edge.target,
    symbol: edge.kind === 'cites' ? ['none', 'arrow'] : ['none', 'none'],
    lineStyle: { type: edge.kind === 'cites' ? 'solid' : 'dashed', opacity: edge.kind === 'cites' ? 0.8 : 0.45 },
    edge,
  }))

  return {
    color: [palette.library, palette.outside],
    tooltip: {
      confine: true,
      formatter: (params: { dataType?: string; data?: { id?: string; edge?: GraphEdge } }) => {
        if (params.dataType === 'edge' && params.data?.edge) return escapeHtml(edgeText(params.data.edge, names))
        const node = byId.get(params.data?.id ?? '')
        if (!node) return ''
        const lines = [`<b>${escapeHtml(node.title)}</b>`]
        const meta = [dateLabel(node), node.venue].filter(Boolean).join(' · ')
        if (meta) lines.push(escapeHtml(meta))
        if (node.cited_by_count !== null) lines.push(`피인용 ${node.cited_by_count.toLocaleString()}`)
        if (node.score !== null) lines.push(`추천 점수 ${node.score.toFixed(2)}`)
        if (node.paper_id !== null && !node.has_data) lines.push('인용 데이터 없음')
        return lines.join('<br>')
      },
    },
    legend: { data: ['서재 논문', '추천 논문'], top: 0, textStyle: { color: palette.text } },
    grid: placed ? { left: 24, right: 160, top: 40, bottom: 40 } : undefined,
    xAxis: year
      ? {
          type: 'category',
          data: year.years.map(String),
          boundaryGap: true,
          axisLine: { onZero: false, lineStyle: { color: palette.edge } },
          axisLabel: { color: palette.text },
          splitLine: { show: true, lineStyle: { color: palette.edge, opacity: 0.25 } },
        }
      : undefined,
    yAxis: placed ? { type: 'value', show: false, inverse: true, min: -0.6, max: stack + 0.6 } : undefined,
    dataZoom: placed ? [{ type: 'inside', xAxisIndex: 0 }] : undefined,
    series: [
      {
        type: 'graph',
        layout: placed ? 'none' : 'force',
        coordinateSystem: placed ? 'cartesian2d' : undefined,
        roam: !placed,
        draggable: !placed,
        force: { repulsion: 420, edgeLength: [80, 220], gravity: 0.05 },
        categories: [{ name: '서재 논문' }, { name: '추천 논문' }],
        data,
        links,
        edgeSymbolSize: 7,
        lineStyle: { color: palette.edge, width: 1.2, curveness: placed ? 0.2 : 0.1 },
        label: { position: placed ? 'top' : 'right', color: palette.text, fontSize: 11 },
        labelLayout: { hideOverlap: true },
        emphasis: { focus: 'adjacency', lineStyle: { width: 2.5 } },
      },
    ],
  }
}
