// @doc: docs/design/CitationStyles.md#6-테스트

import { describe, expect, it, vi } from 'vitest'
import {
  CITATION_STYLES,
  acm,
  apa,
  bibtex,
  bibtexKey,
  chicago,
  copyCitation,
  harvard,
  ieee,
  initials,
  mla,
  splitName,
  vancouver,
  type CitableWork,
} from './citationStyles'

const attention: CitableWork = {
  title: 'Attention Is All You Need',
  authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit', 'Llion Jones', 'Aidan N. Gomez', 'Łukasz Kaiser', 'Illia Polosukhin'],
  item_type: 'conference-paper',
  year: 2017,
  venue: 'Advances in Neural Information Processing Systems',
  doi: '10.48550/arxiv.1706.03762',
  url: null,
}
const lstm: CitableWork = {
  title: 'Long Short-Term Memory',
  authors: ['Sepp Hochreiter', 'Jürgen Schmidhuber'],
  item_type: 'journal-article',
  year: 1997,
  venue: 'Neural Computation',
  doi: '10.1162/neco.1997.9.8.1735',
  url: null,
}
const bert: CitableWork = {
  title: 'BERT: Pre-training of Deep Bidirectional Transformers',
  authors: ['Jacob Devlin'],
  item_type: 'preprint',
  year: 2018,
  venue: null,
  doi: '10.48550/arxiv.1810.04805',
  url: null,
}

describe('이름', () => {
  it('성과 이름을 나누고 머리글자를 만든다', () => {
    expect(splitName('Aidan N. Gomez')).toEqual({ given: 'Aidan N.', family: 'Gomez' })
    expect(splitName('Ludwig van Beethoven')).toEqual({ given: 'Ludwig', family: 'van Beethoven' })
    expect(splitName('Martin Luther King Jr.')).toEqual({ given: 'Martin Luther', family: 'King Jr.' })
    expect(splitName('Gomez, Aidan N.')).toEqual({ given: 'Aidan N.', family: 'Gomez' })
    expect(splitName('Plato')).toEqual({ given: '', family: 'Plato' })
    expect(initials('Aidan N.')).toBe('A. N.')
    expect(initials('Jean-Paul')).toBe('J.-P.')
    expect(initials('Aidan N.', false)).toBe('AN')
  })
})

describe('양식', () => {
  it('APA는 머리글자와 &, 연도, 기울인 게재처, DOI 주소다', () => {
    expect(apa(lstm).text).toBe(
      'Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. Neural Computation. https://doi.org/10.1162/neco.1997.9.8.1735',
    )
    expect(apa(lstm).html).toContain('<i>Neural Computation</i>')
    expect(apa({ ...lstm, year: null }).text).toContain('(n.d.)')
  })

  it('MLA는 셋 이상이면 et al., 둘이면 and로 잇는다', () => {
    expect(mla(attention).text).toBe(
      'Vaswani, Ashish, et al. "Attention Is All You Need." Advances in Neural Information Processing Systems, 2017, https://doi.org/10.48550/arxiv.1706.03762.',
    )
    expect(mla(lstm).text.startsWith('Hochreiter, Sepp, and Jürgen Schmidhuber.')).toBe(true)
  })

  it('Chicago는 첫 저자만 뒤집고 연도를 괄호에 둔다', () => {
    expect(chicago(lstm).text).toBe(
      'Hochreiter, Sepp, and Jürgen Schmidhuber. "Long Short-Term Memory." Neural Computation (1997). https://doi.org/10.1162/neco.1997.9.8.1735',
    )
  })

  it('Harvard는 넷 이상이면 et al.이다', () => {
    expect(harvard(attention).text).toBe(
      "Vaswani, A. et al. (2017) 'Attention Is All You Need', Advances in Neural Information Processing Systems. Available at: https://doi.org/10.48550/arxiv.1706.03762.",
    )
  })

  it('Vancouver는 여섯까지 쓰고 et al.을 붙인다', () => {
    expect(vancouver(attention).text).toBe(
      'Vaswani A, Shazeer N, Parmar N, Uszkoreit J, Jones L, Gomez AN, et al. Attention Is All You Need. Advances in Neural Information Processing Systems. 2017. doi:10.48550/arxiv.1706.03762',
    )
  })

  it('IEEE는 일곱 이상이면 첫 저자 et al., 학회는 in, 저널은 DOI, arXiv는 arXiv 번호다', () => {
    expect(ieee(attention).text).toBe('A. Vaswani et al., "Attention Is All You Need," in Advances in Neural Information Processing Systems, 2017.')
    expect(ieee(attention).html).toContain('<i>et al.</i>')
    expect(ieee(lstm).text).toBe('S. Hochreiter and J. Schmidhuber, "Long Short-Term Memory," Neural Computation, 1997, doi: 10.1162/neco.1997.9.8.1735.')
    expect(ieee(bert).text).toBe('J. Devlin, "BERT: Pre-training of Deep Bidirectional Transformers," arXiv:1810.04805, 2018.')
  })

  it('ACM은 모든 저자, 연도, 학회는 In이다', () => {
    expect(acm(lstm).text).toBe('Sepp Hochreiter and Jürgen Schmidhuber. 1997. Long Short-Term Memory. Neural Computation. https://doi.org/10.1162/neco.1997.9.8.1735')
    expect(acm(attention).text).toContain('. 2017. Attention Is All You Need. In Advances')
  })

  it('BibTeX는 항목 종류에 맞는 형식과 키, arXiv 번호를 쓰고 HTML은 두지 않는다', () => {
    expect(bibtexKey(attention)).toBe('vaswani2017attention')
    const entry = bibtex(bert)
    expect(entry.text).toBe(
      [
        '@article{devlin2018bert,',
        '  title = {{BERT: Pre-training of Deep Bidirectional Transformers}},',
        '  author = {Devlin, Jacob},',
        '  journal = {arXiv preprint arXiv:1810.04805},',
        '  year = {2018},',
        '  eprint = {1810.04805},',
        '  archivePrefix = {arXiv},',
        '  doi = {10.48550/arxiv.1810.04805}',
        '}',
      ].join('\n'),
    )
    expect(entry.html).toBe('')
    expect(bibtex(attention).text.startsWith('@inproceedings{vaswani2017attention,')).toBe(true)
    expect(bibtex(lstm).text).toContain('journal = {Neural Computation}')
    // OpenAlex가 주는 arXiv 저장소 이름은 게재처로 쓰지 않는다.
    const repository = { ...bert, venue: 'arXiv (Cornell University)' }
    expect(bibtex(repository).text).toContain('journal = {arXiv preprint arXiv:1810.04805}')
    expect(ieee(repository).text).toContain('arXiv:1810.04805, 2018.')
  })

  it('HTML은 특수 문자를 바꾸고, 양식은 8가지다', () => {
    expect(apa({ ...lstm, venue: 'A & B <C>' }).html).toContain('<i>A &amp; B &lt;C&gt;</i>')
    expect(CITATION_STYLES.map((style) => style.id)).toEqual(['bibtex', 'ieee', 'acm', 'apa', 'mla', 'chicago', 'harvard', 'vancouver'])
  })
})

describe('copyCitation', () => {
  it('HTML이 있으면 글과 HTML을 함께, 없으면 글만 복사한다', async () => {
    const clipboard = { write: vi.fn().mockResolvedValue(undefined), writeText: vi.fn().mockResolvedValue(undefined) }
    vi.stubGlobal('ClipboardItem', class {
      items: Record<string, Blob>
      constructor(items: Record<string, Blob>) {
        this.items = items
      }
    })
    await copyCitation({ text: 'a', html: '<i>a</i>' }, clipboard as unknown as Clipboard)
    expect(clipboard.write).toHaveBeenCalledTimes(1)
    await copyCitation({ text: '@misc{x}', html: '' }, clipboard as unknown as Clipboard)
    expect(clipboard.writeText).toHaveBeenCalledWith('@misc{x}')
    clipboard.write.mockRejectedValueOnce(new Error('막힘'))
    await copyCitation({ text: 'b', html: '<i>b</i>' }, clipboard as unknown as Clipboard)
    expect(clipboard.writeText).toHaveBeenLastCalledWith('b')
    vi.unstubAllGlobals()
  })
})
