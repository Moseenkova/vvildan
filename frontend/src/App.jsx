import { useEffect, useRef, useState } from 'react'
import DatePicker, { registerLocale } from 'react-datepicker'
import { enUS, ru } from 'date-fns/locale'
import { useLingui } from '@lingui/react/macro'
import 'react-datepicker/dist/react-datepicker.css'
import api from './api'
import { getMessages, locale } from './i18n'
import './App.css'

registerLocale('en', enUS)
registerLocale('ru', ru)

function AirportSearch({ id, label, placeholder, selected, maxSelections, onSelect, onRemove, t }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const containerRef = useRef(null)
  const timeoutRef = useRef(null)
  const requestRef = useRef(0)

  useEffect(() => {
    const closeOnOutsideClick = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', closeOnOutsideClick)
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick)
      clearTimeout(timeoutRef.current)
    }
  }, [])

  const search = async (query) => {
    const trimmedQuery = query.trim()
    const requestId = ++requestRef.current
    if (!trimmedQuery) {
      setResults([])
      setLoading(false)
      return
    }
    setLoading(true)
    setOpen(true)
    try {
      const response = await api.get('/api/airport-search', { params: { q: trimmedQuery } })
      if (requestId === requestRef.current) {
        setResults(Array.isArray(response.data) ? response.data : [])
      }
    } catch (error) {
      if (requestId === requestRef.current) setResults([])
      console.error('Error searching airports:', error)
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }

  const handleInput = (event) => {
    const nextQuery = event.target.value
    setQuery(nextQuery)
    setOpen(Boolean(nextQuery.trim()))
    clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => search(nextQuery), 300)
  }

  const atLimit = selected.length >= maxSelections
  const isMultiple = maxSelections > 1

  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      {selected.length > 0 && (
        <div className="airport-selections">
          {selected.map((airport) => (
            <div className="airport-selection" key={airport.id}>
              <span>{airport.name}, {airport.city_name}, {airport.country_name}</span>
              <button type="button" onClick={() => onRemove(airport.id)} aria-label={`${t.remove} ${airport.name}`}>×</button>
            </div>
          ))}
        </div>
      )}
      {!atLimit && (
        <div className="dropdown-container" ref={containerRef}>
          <input
            id={id}
            type="text"
            value={query}
            onChange={handleInput}
            onFocus={() => query.trim() && search(query)}
            placeholder={placeholder}
            autoComplete="off"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={open}
            aria-controls={`${id}-results`}
            required={selected.length === 0}
          />
          {open && (
          <div id={`${id}-results`} className="dropdown-list" role="listbox">
            {loading ? (
              <div className="dropdown-message">{t.loading}</div>
            ) : results.some((airport) => isMultiple || !selected.some((item) => item.id === airport.id)) ? (
              results.filter((airport) => isMultiple || !selected.some((item) => item.id === airport.id)).map((airport) => {
                const isSelected = selected.some((item) => item.id === airport.id)
                return (
                <button
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  className={`dropdown-item ${isMultiple ? 'dropdown-item-checkbox' : ''}`}
                  key={airport.id}
                  onClick={() => {
                    if (isSelected) onRemove(airport.id)
                    else onSelect(airport)
                    if (!isMultiple) {
                      setQuery('')
                      setResults([])
                      setOpen(false)
                    }
                  }}
                >
                  {isMultiple && <input type="checkbox" checked={isSelected} readOnly tabIndex={-1} />}
                  <span>{airport.name}, {airport.city_name}, {airport.country_name}</span>
                </button>
                )
              })
            ) : (
              <div className="dropdown-message">{t.noAirportsFound}</div>
            )}
          </div>
          )}
        </div>
      )}
    </div>
  )
}

function App() {
  const { _ } = useLingui()
  const language = locale
  const t = getMessages(_)
  const [role, setRole] = useState('sender')
  const [userNotFound, setUserNotFound] = useState(false)
  const [form, setForm] = useState({
    dateFrom: null,
    dateTo: null,
    courierDate: null,
    baggageComments: '',
  })
  const [departureAirports, setDepartureAirports] = useState([])
  const [arrivalAirports, setArrivalAirports] = useState([])

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = ['ar', 'fa', 'ps', 'sd', 'ur'].includes(language) ? 'rtl' : 'ltr'
    window.Telegram?.WebApp?.ready()

    const initAuth = async () => {
      let tgId = null
      if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
        tgId = window.Telegram.WebApp.initDataUnsafe.user.id
      } else if (import.meta.env.VITE_DEV_ENV === 'true') {
        tgId = import.meta.env.VITE_DUMMY_TG_ID
      }
      if (!tgId) return
      try {
        const { data } = await api.post('/auth/login', { tg_id: tgId })
        localStorage.setItem('access_token', data.access_token)
      } catch (error) {
        console.error('Authentication failed:', error)
        if (error.response?.status === 404) setUserNotFound(true)
      }
    }
    initAuth()
  }, [language])

  const setField = (field, value) => setForm((previous) => ({ ...previous, [field]: value }))

  const formatDateToString = (date) => {
    if (!date) return ''
    const day = String(date.getDate()).padStart(2, '0')
    const month = String(date.getMonth() + 1).padStart(2, '0')
    return `${day}.${month}.${date.getFullYear()}`
  }

  const selectAirport = (field, airport) => {
    const update = field === 'departure' ? setDepartureAirports : setArrivalAirports
    const limit = role === 'sender' ? 5 : 1
    update((current) => current.length < limit && !current.some((item) => item.id === airport.id)
      ? [...current, airport]
      : current)
  }

  const removeAirport = (field, airportId) => {
    const update = field === 'departure' ? setDepartureAirports : setArrivalAirports
    update((current) => current.filter((airport) => airport.id !== airportId))
  }

  const changeRole = (nextRole) => {
    setRole(nextRole)
    if (nextRole === 'courier') {
      setDepartureAirports((current) => current.slice(0, 1))
      setArrivalAirports((current) => current.slice(0, 1))
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    if (role === 'sender' && (!form.dateFrom || !form.dateTo)) {
      alert(!form.dateFrom ? t.selectDateFrom : t.selectDateTo)
      return
    }
    if (role === 'sender' && form.dateFrom > form.dateTo) {
      alert(t.invalidDateRange)
      return
    }
    if (role === 'courier' && !form.courierDate) {
      alert(t.selectDate)
      return
    }
    if (!departureAirports.length || !arrivalAirports.length) {
      alert(t.selectAirportFromList)
      return
    }

    const submissionData = {
      role,
      ...(role === 'sender'
        ? { dateFrom: formatDateToString(form.dateFrom), dateTo: formatDateToString(form.dateTo) }
        : { date: formatDateToString(form.courierDate) }),
      departureAirportIds: departureAirports.map((airport) => airport.id),
      arrivalAirportIds: arrivalAirports.map((airport) => airport.id),
      baggageComments: form.baggageComments,
    }
    console.log('Form submitted:', submissionData)
    alert(t.submitted)
  }

  if (userNotFound) {
    return (
      <div className="app-container not-found">
        <h1>404</h1>
        <h2>{t.userNotFound}</h2>
        <p>{t.registrationRequired}</p>
      </div>
    )
  }

  return (
    <div className="app-container">
      <div className="role-selector">
        <button type="button" onClick={() => changeRole('sender')} className={`role-button ${role === 'sender' ? 'active' : ''}`}>{t.sender}</button>
        <button type="button" onClick={() => changeRole('courier')} className={`role-button ${role === 'courier' ? 'active' : ''}`}>{t.courier}</button>
      </div>

      <form onSubmit={handleSubmit} className="order-form">
        {role === 'sender' ? (
          <>
            <div className="form-group">
              <label htmlFor="dateFrom">{t.dateFrom}</label>
              <DatePicker id="dateFrom" selected={form.dateFrom} onChange={(date) => setField('dateFrom', date)} dateFormat={t.dateFormat} placeholderText={t.datePlaceholder} locale={language === 'ru' ? 'ru' : 'en'} className="date-picker-input" required minDate={new Date()} />
            </div>
            <div className="form-group">
              <label htmlFor="dateTo">{t.dateTo}</label>
              <DatePicker id="dateTo" selected={form.dateTo} onChange={(date) => setField('dateTo', date)} dateFormat={t.dateFormat} placeholderText={t.datePlaceholder} locale={language === 'ru' ? 'ru' : 'en'} className="date-picker-input" required minDate={form.dateFrom || new Date()} />
            </div>
          </>
        ) : (
          <div className="form-group">
            <label htmlFor="courierDate">{t.date}</label>
            <DatePicker id="courierDate" selected={form.courierDate} onChange={(date) => setField('courierDate', date)} dateFormat={t.dateFormat} placeholderText={t.datePlaceholder} locale={language === 'ru' ? 'ru' : 'en'} className="date-picker-input" required minDate={new Date()} />
          </div>
        )}

        <AirportSearch id="departure" label={t.departure} placeholder={t.searchAirportCityCountry} selected={departureAirports} maxSelections={role === 'sender' ? 5 : 1} onSelect={(airport) => selectAirport('departure', airport)} onRemove={(airportId) => removeAirport('departure', airportId)} t={t} />
        <AirportSearch id="arrival" label={t.arrival} placeholder={t.searchAirportCityCountry} selected={arrivalAirports} maxSelections={role === 'sender' ? 5 : 1} onSelect={(airport) => selectAirport('arrival', airport)} onRemove={(airportId) => removeAirport('arrival', airportId)} t={t} />

        <div className="form-group">
          <label htmlFor="baggageComments">{t.baggageComments}</label>
          <input type="text" id="baggageComments" value={form.baggageComments} onChange={(event) => setField('baggageComments', event.target.value)} placeholder={t.baggageExample} />
        </div>
        <button type="submit" className="submit-button">{t.submit}</button>
      </form>
    </div>
  )
}

export default App
