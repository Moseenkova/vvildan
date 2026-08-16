import { i18n } from '@lingui/core'
import { msg } from '@lingui/macro'

const supportedLocales = [
  'en', 'zh', 'hi', 'es', 'ar', 'fr', 'bn', 'pt', 'ru', 'ur',
  'id', 'de', 'ja', 'mr', 'te', 'tr', 'ta', 'vi', 'ko', 'fa',
  'ha', 'sw', 'jv', 'it', 'pa', 'gu', 'th', 'kn', 'am', 'bho',
  'yo', 'my', 'pl', 'ml', 'or', 'mai', 'uk', 'ps', 'uz', 'sd',
  'ne', 'si', 'km', 'so', 'ro', 'nl', 'el', 'cs', 'hu', 'fil',
]

const catalogLoaders = import.meta.glob('./locales/*/messages.po', {
  import: 'messages',
})

export const getTelegramLocale = () => {
  const telegramLocale = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
  const browserLocale = navigator.language
  const requestedLocale = (telegramLocale || browserLocale || 'en')
    .toLowerCase()
    .split(/[-_]/)[0]

  return supportedLocales.includes(requestedLocale) ? requestedLocale : 'en'
}

export const locale = getTelegramLocale()

export const activateLocale = async () => {
  const loadCatalog = catalogLoaders[`./locales/${locale}/messages.po`]
  const messages = await loadCatalog()
  i18n.loadAndActivate({ locale, messages })
}

export const getMessages = (_) => ({
  sender: _(msg`Sender`),
  courier: _(msg`Courier`),
  dateFrom: _(msg`From date`),
  dateTo: _(msg`To date`),
  date: _(msg`Date`),
  dateFormat: _(msg`MM/dd/yyyy`),
  datePlaceholder: _(msg`mm/dd/yyyy`),
  departure: _(msg`Departure`),
  arrival: _(msg`Arrival`),
  searchAirportCityCountry: _(msg`Search by airport, city, or country`),
  noAirportsFound: _(msg`No matching airports found`),
  selectAirportFromList: _(msg`Please select departure and arrival airports from the list`),
  countryFrom: _(msg`Departure country`),
  cityFrom: _(msg`Departure city`),
  countryTo: _(msg`Arrival country`),
  cityTo: _(msg`Arrival city`),
  airportFrom: _(msg`Departure airport`),
  airportTo: _(msg`Arrival airport`),
  enterCountry: _(msg`Enter a country`),
  chooseCountryFirst: _(msg`Choose a country first`),
  enterOrChooseCity: _(msg`Enter or choose a city`),
  enterCity: _(msg`Enter a city`),
  enterOrChooseAirport: _(msg`Enter or choose an airport`),
  chooseCityFirst: _(msg`Choose a city first`),
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
