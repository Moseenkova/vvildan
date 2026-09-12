import { defineConfig } from '@lingui/cli'

export default defineConfig({
  locales: [
    'en', 'zh', 'hi', 'es', 'ar', 'fr', 'bn', 'pt', 'ru', 'ur',
    'id', 'de', 'ja', 'mr', 'te', 'tr', 'ta', 'vi', 'ko', 'fa',
    'ha', 'sw', 'jv', 'it', 'pa', 'gu', 'th', 'kn', 'am', 'bho',
    'yo', 'my', 'pl', 'ml', 'or', 'mai', 'uk', 'ps', 'uz', 'sd',
    'ne', 'si', 'km', 'so', 'ro', 'nl', 'el', 'cs', 'hu', 'fil',
  ],
  sourceLocale: 'en',
  catalogs: [{
    path: '<rootDir>/src/locales/{locale}/messages',
    include: ['<rootDir>/src'],
  }],
  format: 'po',
  compileNamespace: 'es',
})
