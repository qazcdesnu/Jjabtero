<!-- @doc: docs/design/PaperSearch.md#4-화면 -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import {
  DuplicatePaperError,
  addPaper,
  searchPapers,
  toPaperInput,
  type SearchResponse,
  type SearchResult,
} from './api'

const SOURCES = [
  { name: 'openalex', label: 'OpenAlex' },
  { name: 'arxiv', label: 'arXiv' },
]

const query = ref('')
const selected = ref(SOURCES.map((source) => source.name))
const searching = ref(false)
const searchError = ref('')
const response = ref<SearchResponse | null>(null)
const tags = reactive<Record<number, string>>({})
const added = reactive<Record<number, boolean>>({})
const addErrors = reactive<Record<number, string>>({})

async function runSearch() {
  if (!query.value.trim() || selected.value.length === 0) return
  searching.value = true
  searchError.value = ''
  try {
    response.value = await searchPapers(query.value, selected.value)
    for (const key of Object.keys(tags)) delete tags[Number(key)]
    for (const key of Object.keys(added)) delete added[Number(key)]
    for (const key of Object.keys(addErrors)) delete addErrors[Number(key)]
  } catch (error) {
    searchError.value = error instanceof Error ? error.message : String(error)
  } finally {
    searching.value = false
  }
}

async function add(index: number, result: SearchResult) {
  delete addErrors[index]
  try {
    await addPaper(toPaperInput(result, tags[index] ?? ''))
    added[index] = true
  } catch (error) {
    if (error instanceof DuplicatePaperError) {
      added[index] = true
    } else {
      addErrors[index] = error instanceof Error ? error.message : String(error)
    }
  }
}
</script>

<template>
  <section class="search">
    <form @submit.prevent="runSearch">
      <input v-model="query" type="search" placeholder="논문 제목, 저자, 주제로 검색" />
      <label v-for="source in SOURCES" :key="source.name">
        <input v-model="selected" type="checkbox" :value="source.name" />
        {{ source.label }}
      </label>
      <button type="submit" :disabled="searching || !query.trim() || selected.length === 0">
        {{ searching ? '검색 중…' : '검색' }}
      </button>
    </form>

    <p v-if="searchError" class="error">{{ searchError }}</p>
    <template v-if="response">
      <p v-for="failure in response.errors" :key="failure.source" class="error">
        {{ failure.source }} 검색 실패: {{ failure.message }}
      </p>
      <p v-if="response.results.length === 0">검색 결과가 없습니다.</p>
      <ol>
        <li v-for="(result, index) in response.results" :key="`${result.source}:${result.source_id}`">
          <a v-if="result.url" :href="result.url" target="_blank" rel="noopener">{{ result.title }}</a>
          <span v-else>{{ result.title }}</span>
          <div class="meta">
            {{ result.authors.join(', ') || '저자 정보 없음' }}
            <span v-if="result.year"> · {{ result.year }}</span>
            <span v-if="result.venue"> · {{ result.venue }}</span>
            · {{ result.source }}
          </div>
          <div class="actions">
            <span v-if="added[index] || result.library_paper_id !== null">서재에 있음</span>
            <template v-else>
              <input v-model="tags[index]" placeholder="태그(쉼표로 구분, 선택)" />
              <button type="button" @click="add(index, result)">서재에 추가</button>
            </template>
            <span v-if="addErrors[index]" class="error">{{ addErrors[index] }}</span>
          </div>
        </li>
      </ol>
    </template>
  </section>
</template>

<style scoped>
form {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
form input[type='search'] {
  flex: 1 1 20rem;
}
li {
  margin-bottom: 0.75rem;
}
.meta {
  color: #555;
  font-size: 0.9em;
}
.actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-top: 0.25rem;
}
.error {
  color: #b00020;
}
</style>
