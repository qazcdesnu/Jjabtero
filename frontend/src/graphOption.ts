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

// @doc: docs/design/CitationGraph.md#4-화면
export function yearLayout(nodes: GraphNode[]): {
  years: number[]
  positions: Map<string, [number, number]>
  hidden: number
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
  years.forEach((year, column) => {
    const group = byYear.get(year)!
    // 같은 연도에서는 서재 논문을 위에, 그다음 피인용 많은 순으로 쌓는다.
    group.sort(
      (a, b) =>
        Number(a.paper_id === null) - Number(b.paper_id === null) ||
        (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0) ||
        a.id.localeCompare(b.id),
    )
    group.forEach((node, index) => positions.set(node.id, [column, index]))
  })
  return { years, positions, hidden }
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
  const year = layout === 'year' ? yearLayout(graph.nodes) : null
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
        const meta = [node.year, node.venue].filter(Boolean).join(' · ')
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
