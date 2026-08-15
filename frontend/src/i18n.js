import { i18n } from '@lingui/core'
import { msg } from '@lingui/macro'
import { messages as enMessages } from './locales/en/messages.po'
import { messages as ruMessages } from './locales/ru/messages.po'

const supportedLocales = ['en', 'ru']

export const getTelegramLocale = () => {
  const telegramLocale = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
  const browserLocale = navigator.language
  const requestedLocale = (telegramLocale || browserLocale || 'en')
    .toLowerCase()
    .split(/[-_]/)[0]

  return supportedLocales.includes(requestedLocale) ? requestedLocale : 'en'
}

export const locale = getTelegramLocale()

i18n.load({ en: enMessages, ru: ruMessages })
i18n.activate(locale)

export const getMessages = (_) => ({
  sender: _(msg`Sender`),
  courier: _(msg`Courier`),
  dateFrom: _(msg`From date`),
  dateTo: _(msg`To date`),
  date: _(msg`Date`),
  dateFormat: _(msg`MM/dd/yyyy`),
  datePlaceholder: _(msg`mm/dd/yyyy`),
  countryFrom: _(msg`Departure country`),
  cityFrom: _(msg`Departure city`),
  countryTo: _(msg`Arrival country`),
  cityTo: _(msg`Arrival city`),
  enterCountry: _(msg`Enter a country`),
  chooseCountryFirst: _(msg`Choose a country first`),
  enterOrChooseCity: _(msg`Enter or choose a city`),
  enterCity: _(msg`Enter a city`),
  loading: _(msg`Loading...`),
  baggageComments: _(msg`Baggage comments`),
  baggageExample: _(msg`For example: Clothes 5 kg, documents, electronics`),
  submit: _(msg`Submit request`),
  selectDateFrom: _(msg`Please select a start date`),
  selectDateTo: _(msg`Please select an end date`),
  invalidDateRange: _(msg`The start date cannot be after the end date`),
  selectDate: _(msg`Please select a date`),
  submitted: _(msg`Form submitted! Check the console for data.`),
  userNotFound: _(msg`User Not Found`),
  registrationRequired: _(msg`You are not registered in the system. Please register through the Telegram bot first.`),
})

export { i18n }
