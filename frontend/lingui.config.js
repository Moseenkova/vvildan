import { defineConfig } from '@lingui/cli'

export default defineConfig({
  locales: ['en', 'ru'],
  sourceLocale: 'en',
  catalogs: [{
    path: '<rootDir>/src/locales/{locale}/messages',
    include: ['<rootDir>/src'],
  }],
  format: 'po',
  compileNamespace: 'es',
})
