// @doc: docs/design/AppSkeleton.md#3-프론트엔드-앱
// @doc: docs/design/UiLayout.md#2-설정과-테마

import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App)
  .use(PrimeVue, {
    theme: {
      preset: Aura,
      options: {
        darkModeSelector: 'system',
        cssLayer: { name: 'primevue', order: 'theme, base, primevue' },
      },
    },
  })
  .directive('tooltip', Tooltip)
  .mount('#app')
