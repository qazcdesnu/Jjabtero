// @doc: docs/design/UiLayout.md#4-테스트와-확인

import { describe, expect, it } from 'vitest'
import { DEFAULT_VIEW, VIEWS } from './navigation'

describe('navigation', () => {
  it('화면 이름은 겹치지 않는다', () => {
    const names = VIEWS.map((view) => view.name)
    expect(new Set(names).size).toBe(names.length)
  })

  it('처음 화면은 논문 검색이고 화면 목록에 있다', () => {
    expect(DEFAULT_VIEW).toBe('search')
    expect(VIEWS.map((view) => view.name)).toContain(DEFAULT_VIEW)
  })
})
