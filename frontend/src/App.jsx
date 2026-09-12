import { useCallback, useEffect, useRef, useState } from 'react'
import DatePicker, { registerLocale } from 'react-datepicker'
import { enUS, ru } from 'date-fns/locale'
import { useLingui } from '@lingui/react/macro'
import 'react-datepicker/dist/react-datepicker.css'
import api from './api'
import TelegramLogin from './TelegramLogin'
import { getMessages, locale } from './i18n'
import './App.css'

registerLocale('en', enUS)
registerLocale('ru', ru)

const formatLocalizedDate = (value, language) => {
  if (!value) return ''

  const dateOnlyParts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  const date = dateOnlyParts
    ? new Date(Number(dateOnlyParts[1]), Number(dateOnlyParts[2]) - 1, Number(dateOnlyParts[3]))
    : new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat(language === 'en' ? 'en-GB' : language, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

function CitySearch({ id, label, placeholder, selected, maxSelections, onSelect, onRemove, t }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [showSearch, setShowSearch] = useState(selected.length === 0)
  const [loading, setLoading] = useState(false)
  const containerRef = useRef(null)
  const inputRef = useRef(null)
  const focusSearchRef = useRef(false)
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

  useEffect(() => {
    if (selected.length === 0) setShowSearch(true)
    if (selected.length >= maxSelections) setShowSearch(false)
  }, [maxSelections, selected.length])

  useEffect(() => {
    if (showSearch && focusSearchRef.current) {
      inputRef.current?.focus()
      focusSearchRef.current = false
    }
  }, [showSearch])

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
      const response = await api.get('/api/search', {
        params: { q: trimmedQuery, language: locale },
      })
      if (requestId === requestRef.current) {
        setResults(Array.isArray(response.data) ? response.data : [])
      }
    } catch (error) {
      if (requestId === requestRef.current) setResults([])
      console.error('Error searching cities:', error)
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

  const handleSelect = (city) => {
    onSelect(city)
    clearTimeout(timeoutRef.current)
    requestRef.current += 1
    setQuery('')
    setResults([])
    setOpen(false)
    setLoading(false)
    setShowSearch(false)
  }

  const handleRemove = (cityId) => {
    onRemove(cityId)
    if (selected.length === 1) setShowSearch(true)
  }

  const showAddSearch = () => {
    focusSearchRef.current = true
    setQuery('')
    setResults([])
    setOpen(false)
    setShowSearch(true)
  }

  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      {selected.length > 0 && (
        <div className="city-selections">
          {selected.map((city) => (
            <div className="city-selection" key={city.id}>
              <span>{city.name}, {city.country_name}</span>
              <button type="button" onClick={() => handleRemove(city.id)} aria-label={`${t.remove} ${city.name}`}>−</button>
            </div>
          ))}
        </div>
      )}
      {isMultiple && selected.length > 0 && !atLimit && !showSearch && (
        <button
          type="button"
          className="city-add-button"
          onClick={showAddSearch}
          aria-label={`${label}: ${placeholder}`}
        >+</button>
      )}
      {!atLimit && showSearch && (
        <div className="dropdown-container" ref={containerRef}>
          <input
            ref={inputRef}
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
            ) : results.some((city) => !selected.some((item) => item.id === city.id)) ? (
              results.filter((city) => !selected.some((item) => item.id === city.id)).map((city) => (
                <button
                  type="button"
                  role="option"
                  aria-selected="false"
                  className="dropdown-item"
                  key={city.id}
                  onClick={() => handleSelect(city)}
                >
                  <span>{city.name}, {city.country_name}</span>
                </button>
              ))
            ) : (
              <div className="dropdown-message">{t.noCitiesFound}</div>
            )}
          </div>
          )}
        </div>
      )}
    </div>
  )
}

function RequestSidebar({ requests, pagination, loading, error, status, onStatusChange, onPageChange, onSelect, t, language }) {
  const route = (request) => {
    const from = request.departure_cities.map((city) => city.name).join(', ')
    const to = request.arrival_cities.map((city) => city.name).join(', ')
    return `${from} → ${to}`
  }

  const dates = (request) => {
    const from = formatLocalizedDate(request.date_from, language)
    const to = formatLocalizedDate(request.date_to, language)
    if (!request.date_from) return to
    if (!request.date_to) return `${from} – ${t.noEndDate}`
    if (request.date_from === request.date_to) return from
    return `${from} – ${to}`
  }

  return (
    <aside className="requests-sidebar">
      <div className="requests-heading">
        <h2>{t.myRequests}</h2>
        <span>{pagination.total}</span>
      </div>
      <label className="status-filter" htmlFor="request-status">
        <span>{t.status}</span>
        <select id="request-status" value={status} onChange={(event) => onStatusChange(event.target.value)}>
          <option value="all">{t.allStatuses}</option>
          <option value="active">{t.active}</option>
          <option value="completed">{t.completed}</option>
          <option value="cancelled">{t.cancelled}</option>
          <option value="expired">{t.expired}</option>
        </select>
      </label>
      <div className="request-list">
        {loading && <p className="request-message">{t.loading}</p>}
        {!loading && error && <p className="request-message request-error">{t.failedToLoadRequests}</p>}
        {!loading && !error && requests.length === 0 && <p className="request-message">{t.noRequests}</p>}
        {!loading && !error && requests.map((request) => (
          <button className="request-card" type="button" key={request.id} onClick={() => onSelect(request)}>
            <span className="request-card-topline">
              <strong>#{request.id}</strong>
              <span className={`status-badge status-${request.status}`}>{t[request.status] || request.status}</span>
            </span>
            <span className="request-route">{route(request)}</span>
            <span className="request-date">{dates(request)}</span>
          </button>
        ))}
      </div>
      {!error && pagination.pages > 1 && (
        <nav className="request-pagination" aria-label={t.pagination}>
          <button
            type="button"
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={loading || pagination.page <= 1}
          >
            {t.previous}
          </button>
          <span>{t.page} {pagination.page} / {pagination.pages}</span>
          <button
            type="button"
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={loading || pagination.page >= pagination.pages}
          >
            {t.next}
          </button>
        </nav>
      )}
    </aside>
  )
}

function RequestDetails({ request, onClose, t, language }) {
  if (!request) return null
  const cities = (items) => items.map((city) => (
    `${city.name}, ${city.country_name}`
  )).join('\n')

  return (
    <div className="details-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="request-details" role="dialog" aria-modal="true" aria-labelledby="request-details-title">
        <div className="details-header">
          <div>
            <p>#{request.id}</p>
            <h2 id="request-details-title">
              {request.role === 'sender' ? t.lookingForCourier : t.willTakeLuggage}
            </h2>
          </div>
          <button type="button" onClick={onClose} aria-label={t.close}>×</button>
        </div>
        <dl>
          <div><dt>{t.status}</dt><dd><span className={`status-badge status-${request.status}`}>{t[request.status] || request.status}</span></dd></div>
          {request.date_from && <div><dt>{request.role === 'sender' ? t.dateFrom : t.date}</dt><dd>{formatLocalizedDate(request.date_from, language)}</dd></div>}
          {request.role === 'sender' && request.date_to && request.date_to !== request.date_from && <div><dt>{t.dateTo}</dt><dd>{formatLocalizedDate(request.date_to, language)}</dd></div>}
          {request.role === 'sender' && request.date_from && !request.date_to && <div><dt>{t.dateTo}</dt><dd>{t.noEndDate}</dd></div>}
          <div><dt>{t.departure}</dt><dd className="multiline">{cities(request.departure_cities)}</dd></div>
          <div><dt>{t.arrival}</dt><dd className="multiline">{cities(request.arrival_cities)}</dd></div>
          {request.comment && <div><dt>{t.comment}</dt><dd>{request.comment}</dd></div>}
          <div><dt>{t.created}</dt><dd>{formatLocalizedDate(request.created_at, language)}</dd></div>
        </dl>
      </section>
    </div>
  )
}

function MatchesList({ matches, loading, error, onSelect, t, language }) {
  const route = (request) => {
    const from = request.departure_cities.map((city) => city.name).join(', ')
    const to = request.arrival_cities.map((city) => city.name).join(', ')
    return `${from} → ${to}`
  }

  const dates = (request) => {
    const from = formatLocalizedDate(request.date_from, language)
    const to = formatLocalizedDate(request.date_to, language)
    if (!request.date_from) return to
    if (!request.date_to) return `${from} – ${t.noEndDate}`
    if (request.date_from === request.date_to) return from
    return `${from} – ${to}`
  }

  return (
    <section className="matches-panel">
      <div className="requests-heading">
        <h2>{t.matches}</h2>
        <span>{matches.length}</span>
      </div>
      <div className="match-list">
        {loading && <p className="request-message">{t.loading}</p>}
        {!loading && error && <p className="request-message request-error">{t.failedToLoadMatches}</p>}
        {!loading && !error && matches.length === 0 && <p className="request-message">{t.noMatches}</p>}
        {!loading && !error && matches.map((match) => (
          <button
            type="button"
            className={`match-card ${match.is_new ? 'match-new' : ''}`}
            key={`${match.is_candidate ? 'candidate' : 'match'}-${match.own_request.id}-${match.id}`}
            onClick={() => onSelect(match.matching_request)}
          >
            <div className="request-card-topline">
              <strong>{t.matchedWith}: {match.matching_user.name}</strong>
              <span className={`status-badge status-${match.status}`}>{t[match.status] || match.status}</span>
            </div>
            {match.matching_user.username && <span className="match-username">@{match.matching_user.username}</span>}
            <span className="request-route">{route(match.matching_request)}</span>
            <span className="request-date">{dates(match.matching_request)}</span>
            {match.matching_request.comment && (
              <p className="match-comment"><strong>{t.comment}:</strong> {match.matching_request.comment}</p>
            )}
            <span className="match-own-request">{t.yourRequest} #{match.own_request.id}</span>
          </button>
        ))}
      </div>
    </section>
  )
}

function App() {
  const { _ } = useLingui()
  const language = locale
  const t = getMessages(_)
  const [authState, setAuthState] = useState('loading')
  const onBrowserLogin = useCallback((token) => {
    localStorage.setItem('access_token', token)
    window.location.reload()
  }, [])
  useEffect(() => {
    const requireLogin = () => setAuthState(window.Telegram?.WebApp?.initData ? 'telegram-error' : 'login')
    window.addEventListener('auth-required', requireLogin)
    return () => window.removeEventListener('auth-required', requireLogin)
  }, [])
  const [role, setRole] = useState('sender')
  const [activePage, setActivePage] = useState(() => (
    new URLSearchParams(window.location.search).get('tab') === 'matches' ? 'matches' : 'new'
  ))
  const [userNotFound, setUserNotFound] = useState(false)
  const [form, setForm] = useState({
    dateFrom: null,
    dateTo: null,
    courierDate: null,
    baggageComments: '',
  })
  const [departureCities, setDepartureCities] = useState([])
  const [arrivalCities, setArrivalCities] = useState([])
  const [requests, setRequests] = useState([])
  const [requestsPagination, setRequestsPagination] = useState({
    page: 1,
    size: 10,
    total: 0,
    pages: 0,
  })
  const [requestsLoading, setRequestsLoading] = useState(true)
  const [requestsError, setRequestsError] = useState(false)
  const [requestStatus, setRequestStatus] = useState('all')
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [matches, setMatches] = useState([])
  const [matchesLoading, setMatchesLoading] = useState(true)
  const [matchesError, setMatchesError] = useState(false)
  const matchesRequestRef = useRef(0)
  const candidateDeepLinkRef = useRef({
    requestId: Number.parseInt(
      new URLSearchParams(window.location.search).get('candidate'),
      10,
    ),
    opened: false,
  })

  const loadRequests = async (page = 1, status = requestStatus) => {
    setRequestsLoading(true)
    setRequestsError(false)
    try {
      const { data } = await api.get('/api/requests', {
        params: {
          page,
          size: requestsPagination.size,
          language,
          ...(status !== 'all' && { status }),
        },
      })
      setRequests(Array.isArray(data.items) ? data.items : [])
      setRequestsPagination((current) => ({
        page: data.page ?? page,
        size: data.size ?? current.size,
        total: data.total ?? 0,
        pages: data.pages ?? 0,
      }))
    } catch (error) {
      console.error('Failed to load requests:', error)
      setRequestsError(true)
    } finally {
      setRequestsLoading(false)
    }
  }

  const loadMatches = async (markSeen = false, silent = false) => {
    const requestId = ++matchesRequestRef.current
    if (!silent) setMatchesLoading(true)
    setMatchesError(false)
    try {
      const { data } = await api.get('/api/matches', { params: { language } })
      if (requestId !== matchesRequestRef.current) return
      const nextMatches = Array.isArray(data) ? data : []
      setMatches(nextMatches)
      if (markSeen && nextMatches.some((match) => match.is_new)) {
        try {
          await api.post('/api/matches/seen')
          setMatches((current) => current.map((match) => ({ ...match, is_new: false })))
        } catch (error) {
          console.error('Failed to mark matches as seen:', error)
        }
      }
    } catch (error) {
      if (requestId !== matchesRequestRef.current) return
      console.error('Failed to load matches:', error)
      setMatchesError(true)
    } finally {
      if (!silent && requestId === matchesRequestRef.current) setMatchesLoading(false)
    }
  }

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = ['ar', 'fa', 'ps', 'sd', 'ur'].includes(language) ? 'rtl' : 'ltr'
    window.Telegram?.WebApp?.ready()

    const initAuth = async () => {
      const initData = window.Telegram?.WebApp?.initData
      const isDev = import.meta.env.VITE_DEV_ENV === 'true'
      if (!initData && !isDev) {
        if (localStorage.getItem('access_token')) {
          setAuthState('authenticated')
          await Promise.all([loadRequests(1), loadMatches(false)])
        } else {
          setAuthState('login')
          setRequestsLoading(false)
        }
        return
      }
      try {
        const { data } = initData
          ? await api.post('/api/auth/login', { init_data: initData })
          : await api.post('/api/auth/dev-login')
        localStorage.setItem('access_token', data.access_token)
        setAuthState('authenticated')
        await Promise.all([loadRequests(1), loadMatches(false)])
      } catch (error) {
        setAuthState(initData ? 'telegram-error' : 'login')
        console.error('Authentication failed:', error)
        if (error.response?.status === 404) setUserNotFound(true)
      }
    }
    initAuth()
    // Authentication and the first page are initialized when the locale changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language])

  useEffect(() => {
    if (authState !== 'authenticated') return undefined
    if (activePage === 'matches') loadMatches(true)

    const refreshMatches = () => loadMatches(activePage === 'matches', true)
    const interval = window.setInterval(refreshMatches, 30000)
    window.addEventListener('focus', refreshMatches)
    return () => {
      window.clearInterval(interval)
      window.removeEventListener('focus', refreshMatches)
    }
    // Match refreshes intentionally follow authentication and the open tab.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePage, authState, language])

  useEffect(() => {
    const deepLink = candidateDeepLinkRef.current
    if (
      activePage !== 'matches'
      || matchesLoading
      || deepLink.opened
      || !Number.isInteger(deepLink.requestId)
    ) return

    const linkedCandidate = matches.find(
      (match) => match.matching_request.id === deepLink.requestId,
    )
    if (linkedCandidate) setSelectedRequest(linkedCandidate.matching_request)
    deepLink.opened = true
  }, [activePage, matches, matchesLoading])

  const changeRequestsPage = async (page) => {
    if (page < 1 || page > requestsPagination.pages || page === requestsPagination.page) return
    setSelectedRequest(null)
    await loadRequests(page)
  }

  const changeRequestStatus = async (status) => {
    setRequestStatus(status)
    setSelectedRequest(null)
    await loadRequests(1, status)
  }

  const setField = (field, value) => setForm((previous) => ({ ...previous, [field]: value }))

  const formatDateToString = (date) => {
    if (!date) return ''
    const day = String(date.getDate()).padStart(2, '0')
    const month = String(date.getMonth() + 1).padStart(2, '0')
    return `${date.getFullYear()}-${month}-${day}`
  }

  const selectCity = (field, city) => {
    const update = field === 'departure' ? setDepartureCities : setArrivalCities
    const limit = role === 'sender' ? 5 : 1
    update((current) => current.length < limit && !current.some((item) => item.id === city.id)
      ? [...current, city]
      : current)
  }

  const removeCity = (field, cityId) => {
    const update = field === 'departure' ? setDepartureCities : setArrivalCities
    update((current) => current.filter((city) => city.id !== cityId))
  }

  const changeRole = (nextRole) => {
    setRole(nextRole)
    if (nextRole === 'courier') {
      setDepartureCities((current) => current.slice(0, 1))
      setArrivalCities((current) => current.slice(0, 1))
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (role === 'sender' && !form.dateFrom && !form.dateTo) {
      alert(`${t.selectDateFrom} / ${t.selectDateTo}`)
      return
    }
    if (role === 'sender' && form.dateTo && form.dateFrom > form.dateTo) {
      alert(t.invalidDateRange)
      return
    }
    if (role === 'courier' && !form.courierDate) {
      alert(t.selectDate)
      return
    }
    if (!departureCities.length || !arrivalCities.length) {
      alert(t.selectCityFromList)
      return
    }

    const submissionData = {
      role,
      dateFrom: formatDateToString(role === 'sender' ? form.dateFrom : form.courierDate) || null,
      dateTo: role === 'sender'
        ? formatDateToString(form.dateTo) || null
        : formatDateToString(form.courierDate),
      departureCityIds: departureCities.map((city) => city.id),
      arrivalCityIds: arrivalCities.map((city) => city.id),
      baggageComments: form.baggageComments,
    }
    try {
      await api.post('/api/requests', submissionData)
      setForm({ dateFrom: null, dateTo: null, courierDate: null, baggageComments: '' })
      setDepartureCities([])
      setArrivalCities([])
      await loadRequests(1)
      await loadMatches(activePage === 'matches')
      alert(t.submitted)
    } catch (error) {
      console.error('Failed to submit request:', error)
      alert(error.response?.data?.detail || 'Failed to submit request')
    }
  }

  if (authState === 'telegram-error' && !userNotFound) return (
    <main className="app-container not-found">
      <h1>Unable to sign in through Telegram</h1>
      <p role="alert">Please reopen this app from the bot to refresh your Telegram session, or try again.</p>
      <button type="button" onClick={() => window.location.reload()}>Try again</button>
    </main>
  )
  if (authState === 'loading') return <main className="app-container"><p role="status">{t.loading}</p></main>
  if (authState === 'login' && !userNotFound) return <TelegramLogin onLogin={onBrowserLogin} registrationMessage={t.registrationRequired} />

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
    <div className="page-shell">
      <main className="app-container">
      <div className="role-selector page-navigation">
        <button type="button" onClick={() => setActivePage('new')} className={`role-button ${activePage === 'new' ? 'active' : ''}`}>{t.newRequest}</button>
        <button type="button" onClick={() => setActivePage('requests')} className={`role-button ${activePage === 'requests' ? 'active' : ''}`}>{t.myRequests}</button>
        <button
          type="button"
          onClick={() => setActivePage('matches')}
          className={`role-button match-tab ${activePage === 'matches' ? 'active' : ''}`}
        >
          {t.matches}
          {matches.some((match) => match.is_new) && (
            <span className="new-match-dot" aria-label={t.newMatches} role="status" />
          )}
        </button>
      </div>

      {activePage === 'new' ? (
      <form onSubmit={handleSubmit} className="order-form">
        <div className="form-group">
          <label htmlFor="requestRole">{t.role}</label>
          <select id="requestRole" className="form-select" value={role} onChange={(event) => changeRole(event.target.value)}>
            <option value="sender">{t.sender}</option>
            <option value="courier">{t.courier}</option>
          </select>
        </div>
        {role === 'sender' ? (
          <>
            <div className="form-group">
              <label htmlFor="dateFrom">{t.dateFrom}</label>
              <DatePicker id="dateFrom" selected={form.dateFrom} onChange={(date) => setField('dateFrom', date)} dateFormat={t.dateFormat} placeholderText={t.datePlaceholder} locale={language === 'ru' ? 'ru' : 'en'} className="date-picker-input" isClearable minDate={new Date()} maxDate={form.dateTo || undefined} />
            </div>
            <div className="form-group">
              <label htmlFor="dateTo">{t.dateTo}</label>
              <DatePicker id="dateTo" selected={form.dateTo} onChange={(date) => setField('dateTo', date)} dateFormat={t.dateFormat} placeholderText={t.datePlaceholder} locale={language === 'ru' ? 'ru' : 'en'} className="date-picker-input" isClearable minDate={form.dateFrom || new Date()} />
            </div>
          </>
        ) : (
          <div className="form-group">
            <label htmlFor="courierDate">{t.date}</label>
            <DatePicker id="courierDate" selected={form.courierDate} onChange={(date) => setField('courierDate', date)} dateFormat={t.dateFormat} placeholderText={t.datePlaceholder} locale={language === 'ru' ? 'ru' : 'en'} className="date-picker-input" required minDate={new Date()} />
          </div>
        )}

        <CitySearch id="departure" label={t.departure} placeholder={t.searchCityCountry} selected={departureCities} maxSelections={role === 'sender' ? 5 : 1} onSelect={(city) => selectCity('departure', city)} onRemove={(cityId) => removeCity('departure', cityId)} t={t} />
        <CitySearch id="arrival" label={t.arrival} placeholder={t.searchCityCountry} selected={arrivalCities} maxSelections={role === 'sender' ? 5 : 1} onSelect={(city) => selectCity('arrival', city)} onRemove={(cityId) => removeCity('arrival', cityId)} t={t} />

        <div className="form-group">
          <label htmlFor="baggageComments">{t.baggageComments}</label>
          <input type="text" id="baggageComments" value={form.baggageComments} onChange={(event) => setField('baggageComments', event.target.value)} placeholder={t.baggageExample} />
        </div>
        <button type="submit" className="submit-button">{t.submit}</button>
      </form>
      ) : activePage === 'requests' ? (
        <RequestSidebar requests={requests} pagination={requestsPagination} loading={requestsLoading} error={requestsError} status={requestStatus} onStatusChange={changeRequestStatus} onPageChange={changeRequestsPage} onSelect={setSelectedRequest} t={t} language={language} />
      ) : (
        <MatchesList matches={matches} loading={matchesLoading} error={matchesError} onSelect={setSelectedRequest} t={t} language={language} />
      )}
      </main>
      <RequestDetails request={selectedRequest} onClose={() => setSelectedRequest(null)} t={t} language={language} />
    </div>
  )
}

export default App
