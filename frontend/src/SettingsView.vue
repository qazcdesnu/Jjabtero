<!-- @doc: docs/design/Settings.md#4-화면 -->
<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import { onMounted } from 'vue'
import { createSettingsState } from './settingsState'

const settings = createSettingsState()
onMounted(() => settings.load())
</script>

<template>
  <section class="mx-auto flex max-w-2xl flex-col gap-6 p-6">
    <header>
      <h2 class="text-xl font-semibold">설정</h2>
      <p class="text-sm text-surface-500">바꾼 설정은 서재와 함께 구글 드라이브에 보관되어 다른 컴퓨터에서도 같은 값을 씁니다.</p>
    </header>

    <p v-if="settings.state.loading" class="text-sm text-surface-500">불러오는 중…</p>

    <form v-else class="flex flex-col gap-6" @submit.prevent="settings.save()">
      <div
        v-for="item in settings.state.items"
        :key="item.key"
        class="flex flex-col gap-2 rounded-lg border border-surface-200 p-4 dark:border-surface-700"
      >
        <label :for="`setting-${item.key}`" class="font-medium">{{ item.label }}</label>
        <p class="text-sm text-surface-500">{{ item.description }}</p>
        <div class="flex flex-wrap items-center gap-3">
          <InputNumber
            v-model="settings.state.draft[item.key]"
            :input-id="`setting-${item.key}`"
            :min="item.minimum"
            :max="item.maximum"
            :use-grouping="false"
            show-buttons
            input-class="w-24"
          />
          <span class="text-xs text-surface-500">
            {{ item.minimum }}~{{ item.maximum }}, 기본값 {{ item.default }}
          </span>
          <Button
            label="기본값으로"
            size="small"
            text
            severity="secondary"
            :disabled="settings.state.draft[item.key] === item.default"
            @click="settings.resetToDefault(item.key)"
          />
        </div>
      </div>

      <div class="flex items-center gap-3">
        <Button type="submit" label="저장" icon="pi pi-check" :loading="settings.state.saving" :disabled="!settings.dirty.value" />
        <Message v-if="settings.state.message" severity="success" size="small" variant="simple">
          {{ settings.state.message }}
        </Message>
      </div>
    </form>

    <Message v-if="settings.state.error" severity="error">{{ settings.state.error }}</Message>
  </section>
</template>
