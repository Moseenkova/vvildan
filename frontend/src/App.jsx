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

function AirportSearch({ id, label, placeholder, value, onChange, onSelect, t }) {
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
    const query = event.target.value
    onChange(query)
    setOpen(Boolean(query.trim()))
    clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => search(query), 300)
  }

  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      <div className="dropdown-container" ref={containerRef}>
        <input
          id={id}
          type="text"
          value={value}
          onChange={handleInput}
          onFocus={() => value.trim() && search(value)}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={`${id}-results`}
          required
        />
        {open && (
          <div id={`${id}-results`} className="dropdown-list" role="listbox">
            {loading ? (
              <div className="dropdown-message">{t.loading}</div>
            ) : results.length ? (
              results.map((airport) => (
                <button
                  type="button"
                  role="option"
                  className="dropdown-item"
                  key={airport.id}
                  onClick={() => {
                    onSelect(airport)
                    setOpen(false)
                  }}
                >
                  {airport.name}, {airport.city_name}, {airport.country_name}
                </button>
              ))
            ) : (
              <div className="dropdown-message">{t.noAirportsFound}</div>
            )}
          </div>
        )}
      </div>
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
    departure: '',
    arrival: '',
    baggageComments: '',
  })
  const [departureAirport, setDepartureAirport] = useState(null)
  const [arrivalAirport, setArrivalAirport] = useState(null)

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

  const selectLocation = (field, airport) => {
    setField(field, `${airport.name}, ${airport.city_name}, ${airport.country_name}`)
    if (field === 'departure') setDepartureAirport(airport)
    else setArrivalAirport(airport)
  }

  const changeLocation = (field, value) => {
    setField(field, value)
    if (field === 'departure') setDepartureAirport(null)
    else setArrivalAirport(null)
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
    if (!departureAirport || !arrivalAirport) {
      alert(t.selectAirportFromList)
      return
    }

    const submissionData = {
      role,
      ...(role === 'sender'
        ? { dateFrom: formatDateToString(form.dateFrom), dateTo: formatDateToString(form.dateTo) }
        : { date: formatDateToString(form.courierDate) }),
      countryFrom: departureAirport.country_name,
      cityFrom: departureAirport.city_name,
      airportFrom: departureAirport.name,
      airportFromId: departureAirport.id,
      countryTo: arrivalAirport.country_name,
      cityTo: arrivalAirport.city_name,
      airportTo: arrivalAirport.name,
      airportToId: arrivalAirport.id,
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
        <button type="button" onClick={() => setRole('sender')} className={`role-button ${role === 'sender' ? 'active' : ''}`}>{t.sender}</button>
        <button type="button" onClick={() => setRole('courier')} className={`role-button ${role === 'courier' ? 'active' : ''}`}>{t.courier}</button>
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

        <AirportSearch id="departure" label={t.departure} placeholder={t.searchAirportCityCountry} value={form.departure} onChange={(value) => changeLocation('departure', value)} onSelect={(airport) => selectLocation('departure', airport)} t={t} />
        <AirportSearch id="arrival" label={t.arrival} placeholder={t.searchAirportCityCountry} value={form.arrival} onChange={(value) => changeLocation('arrival', value)} onSelect={(airport) => selectLocation('arrival', airport)} t={t} />

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
