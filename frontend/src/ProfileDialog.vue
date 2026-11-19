<!-- @doc: docs/design/AiChat.md#6-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Select from 'primevue/select'
import { computed, ref, watch } from 'vue'
import { formatDateTime } from './labels'
import { createProfileState } from './profileState'

// email: 로그인한 계정. 로그인이 꺼진 내 컴퓨터에서는 null이다.
defineProps<{ email: string | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ changed: [] }>()
const profile = createProfileState()
const confirmingDelete = ref(false)
// 고른 모델이 오늘 무료 목록에 없는지. 목록을 받은 뒤에만 따진다.
const chosenNotFree = computed(() => {
  const chosen = profile.state.status?.model
  return Boolean(chosen && profile.state.modelsCheckedAt && !profile.state.models.some((model) => model.name === chosen))
})
// 고른 모델의 정보(가격)
const chosenModel = computed(() => profile.state.models.find((model) => model.name === profile.state.status?.model) ?? null)
// 목록을 못 받았어도 고른 모델 이름은 보이게 한다.
const modelOptions = computed(() => {
  const chosen = profile.state.status?.model
  const models = profile.state.models
  if (chosen && !models.some((model) => model.name === chosen)) return [{ name: chosen, label: chosen, description: '' }, ...models]
  return models
})

watch(visible, (open) => {
  confirmingDelete.value = false
  if (open) void profile.load()
})

async function saveKey() {
  await profile.saveKey()
  emit('changed')
}

async function removeKey() {
  confirmingDelete.value = false
  await profile.removeKey()
  emit('changed')
}

async function chooseModel(model: string) {
  await profile.chooseModel(model)
  emit('changed')
}
</script>

<template>
  <Dialog v-model:visible="visible" modal header="프로필" :style="{ width: '32rem' }" :breakpoints="{ '640px': '95vw' }">
    <div class="flex flex-col gap-5">
      <section class="flex flex-col gap-1">
        <span class="text-xs text-surface-500">계정</span>
        <span class="text-sm">{{ email ?? '내 컴퓨터 (로그인 꺼짐)' }}</span>
      </section>

      <section class="flex flex-col gap-2" aria-label="Google AI API 키">
        <span class="text-sm font-medium">Google AI API 키</span>
        <p class="text-xs text-surface-500">
          리더에서 고른 글로 Gemini와 대화할 때 씁니다. 키는 암호화해 저장하고 다시 보여 주지 않습니다.
          <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener" class="text-primary hover:underline">키 만들기</a>
        </p>
        <Message v-if="profile.state.status && !profile.state.status.master_key && profile.state.status.registered" severity="warn" size="small">
          암호화 키가 없어 등록된 키를 쓸 수 없습니다.
        </Message>
        <Message v-else-if="profile.state.status?.registered && !profile.state.status.usable" severity="warn" size="small">
          등록된 키를 이곳의 암호화 키로 풀 수 없습니다. 키를 다시 등록하세요.
        </Message>

        <div v-if="profile.state.status?.registered && !profile.state.editing" class="flex flex-wrap items-center gap-2">
          <span class="text-sm">등록됨 <span class="font-mono text-surface-500">(…{{ profile.state.status.hint }})</span></span>
          <span class="flex-1" />
          <template v-if="!confirmingDelete">
            <Button label="변경" icon="pi pi-pencil" size="small" severity="secondary" outlined :disabled="profile.state.busy" @click="profile.startEdit()" />
            <Button label="삭제" icon="pi pi-trash" size="small" severity="danger" outlined :disabled="profile.state.busy" @click="confirmingDelete = true" />
          </template>
          <template v-else>
            <span class="text-sm">키를 지울까요?</span>
            <Button label="취소" size="small" severity="secondary" text @click="confirmingDelete = false" />
            <Button label="지우기" size="small" severity="danger" :loading="profile.state.busy" @click="removeKey" />
          </template>
        </div>

        <form v-else class="flex flex-wrap items-center gap-2" @submit.prevent="saveKey">
          <Password
            v-model="profile.state.keyInput"
            :feedback="false"
            toggle-mask
            placeholder="API 키 붙여넣기"
            input-class="w-full"
            class="min-w-0 flex-1"
            :input-props="{ autocomplete: 'off', 'aria-label': 'Google AI API 키' }"
          />
          <Button
            type="submit"
            :label="profile.state.status?.registered ? '바꾸기' : '등록'"
            size="small"
            :loading="profile.state.busy"
            :disabled="!profile.state.keyInput.trim()"
          />
          <Button v-if="profile.state.status?.registered" label="취소" size="small" severity="secondary" text @click="profile.cancelEdit()" />
        </form>

        <div v-if="profile.state.status?.usable" class="flex flex-col gap-1">
          <label for="profile-ai-model" class="text-xs text-surface-500">모델</label>
          <Select
            input-id="profile-ai-model"
            :model-value="profile.state.status.model"
            :options="modelOptions"
            option-label="label"
            option-value="name"
            placeholder="Gemini 모델 고르기"
            :loading="profile.state.models.length === 0 && profile.state.busy"
            :disabled="profile.state.busy"
            filter
            @update:model-value="chooseModel"
          >
            <template #option="{ option }">
              <div class="flex min-w-0 flex-col">
                <span class="text-sm">{{ option.label }} <span class="text-xs text-surface-500">{{ option.name }}</span></span>
                <span v-if="option.input_price" class="whitespace-normal text-xs text-surface-500">
                  입력 {{ option.input_price }} · 출력 {{ option.output_price || '-' }}
                </span>
              </div>
            </template>
          </Select>
          <div v-if="chosenModel?.input_price" class="rounded-md bg-surface-50 px-2 py-1.5 text-xs dark:bg-surface-800">
            <span class="font-medium">{{ chosenModel.label }}</span> 유료 등급 가격(100만 토큰당, USD):
            입력 {{ chosenModel.input_price }} · 출력 {{ chosenModel.output_price || '-' }}
          </div>
          <span class="text-xs text-surface-500">
            무료 등급은 한도 안에서 무료이고, 가격은 결제를 켠 키(유료 등급)에 청구되는 값입니다.
            구글 가격표에서 오늘 무료 등급인 모델만 보입니다. 매일 자정(한국 시각)에 다시 확인합니다.
            <template v-if="profile.state.modelsCheckedAt">마지막 확인 {{ formatDateTime(profile.state.modelsCheckedAt) }}.</template>
          </span>
          <Message v-if="profile.state.modelsStale" severity="warn" size="small">오늘 가격표를 읽지 못해 지난 목록을 보입니다.</Message>
          <Message v-if="chosenNotFree" severity="warn" size="small">
            고른 모델이 오늘 무료 목록에 없습니다. 무료로 쓰려면 다른 모델을 고르세요.
          </Message>
        </div>

        <Message v-if="profile.state.message" severity="success" size="small" variant="simple">{{ profile.state.message }}</Message>
        <Message v-if="profile.state.error" severity="error" size="small">{{ profile.state.error }}</Message>
      </section>
    </div>
  </Dialog>
</template>
