import { useState, useEffect, useRef } from 'react'
import DatePicker, { registerLocale } from 'react-datepicker'
import { enUS, ru } from 'date-fns/locale'
import { useLingui } from '@lingui/react/macro'
import 'react-datepicker/dist/react-datepicker.css'
import api from './api'
import { getMessages, locale } from './i18n'
import './App.css'

registerLocale('en', enUS)
registerLocale('ru', ru)

function App() {
  const { _ } = useLingui()
  const language = locale
  const t = getMessages(_)
  const [role, setRole] = useState("sender");
  const [userNotFound, setUserNotFound] = useState(false);
  const [form, setForm] = useState({
    dateFrom: null,
    dateTo: null,
    courierDate: null,
    countryFrom: "",
    cityFrom: "",
    countryTo: "",
    cityTo: "",
    airportFrom: "",
    airportTo: "",
    baggageComments: "",
  });
  const [countries, setCountries] = useState([]);
  const [showCountryFromDropdown, setShowCountryFromDropdown] = useState(false);
  const [showCountryToDropdown, setShowCountryToDropdown] = useState(false);
  const [loadingCountries, setLoadingCountries] = useState(false);
  const countryFromDropdownRef = useRef(null);
  const countryToDropdownRef = useRef(null);
  const countrySearchTimeoutRef = useRef(null);

  // Country IDs when selected from dropdown (null if typed manually)
  const [countryFromId, setCountryFromId] = useState(null);
  const [countryToId, setCountryToId] = useState(null);
  const [cityFromId, setCityFromId] = useState(null);
  const [cityToId, setCityToId] = useState(null);
  const [airportFromId, setAirportFromId] = useState(null);
  const [airportToId, setAirportToId] = useState(null);

  // City dropdown state
  const [cities, setCities] = useState([]);
  const [showCityFromDropdown, setShowCityFromDropdown] = useState(false);
  const [showCityToDropdown, setShowCityToDropdown] = useState(false);
  const [loadingCities, setLoadingCities] = useState(false);
  const cityFromDropdownRef = useRef(null);
  const cityToDropdownRef = useRef(null);
  const citySearchTimeoutRef = useRef(null);

  const [airports, setAirports] = useState([]);
  const [showAirportFromDropdown, setShowAirportFromDropdown] = useState(false);
  const [showAirportToDropdown, setShowAirportToDropdown] = useState(false);
  const [loadingAirports, setLoadingAirports] = useState(false);
  const airportFromDropdownRef = useRef(null);
  const airportToDropdownRef = useRef(null);
  const airportSearchTimeoutRef = useRef(null);

  // Authentication effect for Telegram Web App
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = ['ar', 'fa', 'ps', 'sd', 'ur'].includes(language) ? 'rtl' : 'ltr';
    window.Telegram?.WebApp?.ready();

    const initAuth = async () => {
      // Get tg_id from Telegram Web App or use a fallback for local testing
      let tg_id = null;
      if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
        tg_id = window.Telegram.WebApp.initDataUnsafe.user.id;
      } else if (import.meta.env.VITE_DEV_ENV === 'true') {
        // Fallback for development if not in Telegram and dev env is specified
        tg_id = import.meta.env.VITE_DUMMY_TG_ID;
      }

      if (!tg_id) {
        console.warn("No Telegram user ID found and dev fallback is disabled.");
        return;
      }

      try {
        const { data } = await api.post('/auth/login', { tg_id });
        localStorage.setItem("access_token", data.access_token);
        console.log("Authenticated successfully!");
      } catch (error) {
        console.error("Authentication failed:", error);
        if (error.response?.status === 404) {
          setUserNotFound(true);
        }
      }
    };

    initAuth();
  }, [language]);

  // Format Date object to dd.mm.yyyy string
  const formatDateToString = (date) => {
    if (!date) return "";
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}.${month}.${year}`;
  };

  const handleDateChange = (date, fieldName) => {
    setForm((prev) => ({
      ...prev,
      [fieldName]: date,
    }));
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const fetchCountries = async (searchQuery = '', field = 'from') => {
    setLoadingCountries(true);
    if (field === 'from') {
      setShowCountryFromDropdown(true);
      setShowCountryToDropdown(false);
    } else {
      setShowCountryToDropdown(true);
      setShowCountryFromDropdown(false);
    }
    try {
      const q = encodeURIComponent(searchQuery);
      const response = await api.get(`/api/countries?q=${q}`);
      const data = response.data;
      setCountries(Array.isArray(data) ? data : []);
    } catch (error) {
      setCountries([]);
      console.error('Error fetching countries:', error);
    } finally {
      setLoadingCountries(false);
    }
  };

  const handleCountrySelect = (country, field) => {
    const countryName = typeof country === 'string' ? country : country.name;
    const countryId = typeof country === 'object' ? country.id : null;
    setForm((prev) => ({
      ...prev,
      [field]: countryName,
      [field === 'countryFrom' ? 'cityFrom' : 'cityTo']: '',
      [field === 'countryFrom' ? 'airportFrom' : 'airportTo']: '',
    }));
    if (field === 'countryFrom') {
      setCountryFromId(countryId);
      setCityFromId(null);
      setAirportFromId(null);
      setShowCountryFromDropdown(false);
    } else {
      setCountryToId(countryId);
      setCityToId(null);
      setAirportToId(null);
      setShowCountryToDropdown(false);
    }
  };

  const fetchCities = async (countryId, searchQuery = '', field = 'from') => {
    if (!countryId) return;
    setLoadingCities(true);
    if (field === 'from') {
      setShowCityFromDropdown(true);
      setShowCityToDropdown(false);
    } else {
      setShowCityToDropdown(true);
      setShowCityFromDropdown(false);
    }
    try {
      const q = encodeURIComponent(searchQuery);
      const response = await api.get(`/api/cities?country_id=${countryId}&q=${q}`);
      const data = response.data;
      setCities(Array.isArray(data) ? data : []);
    } catch (error) {
      setCities([]);
      console.error('Error fetching cities:', error);
    } finally {
      setLoadingCities(false);
    }
  };

  const handleCitySelect = (city, field) => {
    setForm((prev) => ({
      ...prev,
      [field]: city.name,
      [field === 'cityFrom' ? 'airportFrom' : 'airportTo']: '',
    }));
    if (field === 'cityFrom') {
      setCityFromId(city.id);
      setAirportFromId(null);
      setShowCityFromDropdown(false);
    } else {
      setCityToId(city.id);
      setAirportToId(null);
      setShowCityToDropdown(false);
    }
  };

  const fetchAirports = async (cityId, searchQuery = '', field = 'from') => {
    if (!cityId) return;
    setLoadingAirports(true);
    setShowAirportFromDropdown(field === 'from');
    setShowAirportToDropdown(field === 'to');
    try {
      const q = encodeURIComponent(searchQuery);
      const response = await api.get(`/api/airports?city_id=${cityId}&q=${q}`);
      setAirports(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      setAirports([]);
      console.error('Error fetching airports:', error);
    } finally {
      setLoadingAirports(false);
    }
  };

  const handleAirportSelect = (airport, field) => {
    setForm((prev) => ({ ...prev, [field]: airport.name }));
    if (field === 'airportFrom') {
      setAirportFromId(airport.id);
      setShowAirportFromDropdown(false);
    } else {
      setAirportToId(airport.id);
      setShowAirportToDropdown(false);
    }
  };

  const handleAirportChange = (e, field) => {
    handleChange(e);
    if (field === 'airportFrom') setAirportFromId(null);
    else setAirportToId(null);
  };

  // Clear countryId when user types in country field (manual input)
  const handleCountryChange = (e, field) => {
    const cityField = field === 'countryFrom' ? 'cityFrom' : 'cityTo';
    const airportField = field === 'countryFrom' ? 'airportFrom' : 'airportTo';
    setForm((prev) => ({
      ...prev,
      [field]: e.target.value,
      [cityField]: '',
      [airportField]: '',
    }));
    if (field === 'countryFrom') {
      setCountryFromId(null);
      setCityFromId(null);
      setAirportFromId(null);
    } else {
      setCountryToId(null);
      setCityToId(null);
      setAirportToId(null);
    }
  };

  const handleCityChange = (e, field) => {
    const airportField = field === 'cityFrom' ? 'airportFrom' : 'airportTo';
    setForm((prev) => ({
      ...prev,
      [field]: e.target.value,
      [airportField]: '',
    }));
    if (field === 'cityFrom') {
      setCityFromId(null);
      setAirportFromId(null);
    } else {
      setCityToId(null);
      setAirportToId(null);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (countryFromDropdownRef.current && !countryFromDropdownRef.current.contains(event.target)) {
        setShowCountryFromDropdown(false);
      }
      if (countryToDropdownRef.current && !countryToDropdownRef.current.contains(event.target)) {
        setShowCountryToDropdown(false);
      }
      if (cityFromDropdownRef.current && !cityFromDropdownRef.current.contains(event.target)) {
        setShowCityFromDropdown(false);
      }
      if (cityToDropdownRef.current && !cityToDropdownRef.current.contains(event.target)) {
        setShowCityToDropdown(false);
      }
      if (airportFromDropdownRef.current && !airportFromDropdownRef.current.contains(event.target)) {
        setShowAirportFromDropdown(false);
      }
      if (airportToDropdownRef.current && !airportToDropdownRef.current.contains(event.target)) {
        setShowAirportToDropdown(false);
      }
    };

    if (showCountryFromDropdown || showCountryToDropdown || showCityFromDropdown || showCityToDropdown || showAirportFromDropdown || showAirportToDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showCountryFromDropdown, showCountryToDropdown, showCityFromDropdown, showCityToDropdown, showAirportFromDropdown, showAirportToDropdown]);

  const handleSubmit = (e) => {
    e.preventDefault();

    // Validate dates
    if (role === "sender") {
      if (!form.dateFrom) {
        alert(t.selectDateFrom);
        return;
      }
      if (!form.dateTo) {
        alert(t.selectDateTo);
        return;
      }

      if (form.dateFrom > form.dateTo) {
        alert(t.invalidDateRange);
        return;
      }
    } else if (role === "courier") {
      if (!form.courierDate) {
        alert(t.selectDate);
        return;
      }
    }

    // Prepare submission data with formatted dates
    const submissionData = {
      role,
      ...(role === "sender"
        ? {
          dateFrom: formatDateToString(form.dateFrom),
          dateTo: formatDateToString(form.dateTo)
        }
        : { date: formatDateToString(form.courierDate) }
      ),
      countryFrom: form.countryFrom,
      cityFrom: form.cityFrom,
      airportFrom: form.airportFrom,
      airportFromId,
      countryTo: form.countryTo,
      cityTo: form.cityTo,
      airportTo: form.airportTo,
      airportToId,
      baggageComments: form.baggageComments,
    };

    console.log("Form submitted:", submissionData);
    alert(t.submitted);

    // Here you would typically send data to your backend API
  };

  if (userNotFound) {
    return (
      <div className="app-container" style={{ textAlign: "center", padding: "50px 20px" }}>
        <h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>404</h1>
        <h2>{t.userNotFound}</h2>
        <p style={{ marginTop: "1rem", color: "#666" }}>
          {t.registrationRequired}
        </p>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="role-selector">
        <button
          onClick={() => setRole("sender")}
          className={`role-button ${role === "sender" ? "active" : ""}`}
        >
          {t.sender}
        </button>
        <button
          onClick={() => setRole("courier")}
          className={`role-button ${role === "courier" ? "active" : ""}`}
        >
          {t.courier}
        </button>
      </div>

      <form onSubmit={handleSubmit} className="order-form">
        {/* Role-dependent date fields */}
        {role === "sender" && (
          <>
            <div className="form-group">
              <label htmlFor="dateFrom">{t.dateFrom}</label>
              <DatePicker
                id="dateFrom"
                selected={form.dateFrom}
                onChange={(date) => handleDateChange(date, 'dateFrom')}
                dateFormat={t.dateFormat}
                placeholderText={t.datePlaceholder}
                locale={language === 'ru' ? 'ru' : 'en'}
                className="date-picker-input"
                required
                minDate={new Date()}
              />
            </div>
            <div className="form-group">
              <label htmlFor="dateTo">{t.dateTo}</label>
              <DatePicker
                id="dateTo"
                selected={form.dateTo}
                onChange={(date) => handleDateChange(date, 'dateTo')}
                dateFormat={t.dateFormat}
                placeholderText={t.datePlaceholder}
                locale={language === 'ru' ? 'ru' : 'en'}
                className="date-picker-input"
                required
                minDate={form.dateFrom || new Date()}
              />
            </div>
          </>
        )}

        {role === "courier" && (
          <div className="form-group">
            <label htmlFor="courierDate">{t.date}</label>
            <DatePicker
              id="courierDate"
              selected={form.courierDate}
              onChange={(date) => handleDateChange(date, 'courierDate')}
              dateFormat={t.dateFormat}
              placeholderText={t.datePlaceholder}
              locale={language === 'ru' ? 'ru' : 'en'}
              className="date-picker-input"
              required
              minDate={new Date()}
            />
          </div>
        )}

        {/* Common fields */}
        <div className="form-group">
          <label htmlFor="countryFrom">{t.countryFrom}</label>
          <div className="dropdown-container" ref={countryFromDropdownRef}>
            <input
              type="text"
              id="countryFrom"
              name="countryFrom"
              value={form.countryFrom}
              onChange={(e) => {
                handleCountryChange(e, 'countryFrom');
                if (countrySearchTimeoutRef.current) clearTimeout(countrySearchTimeoutRef.current);
                countrySearchTimeoutRef.current = setTimeout(() => {
                  if (showCountryFromDropdown) fetchCountries(e.target.value, 'from');
                }, 300);
              }}
              onFocus={() => fetchCountries(form.countryFrom, 'from')}
              onClick={() => fetchCountries(form.countryFrom, 'from')}
              required
              placeholder={t.enterCountry}
            />
            {showCountryFromDropdown && (
              <div className="dropdown-list">
                {loadingCountries ? (
                  <div className="dropdown-item">{t.loading}</div>
                ) : countries.length > 0 ? (
                  countries.map((country) => (
                    <div
                      key={country.id}
                      className="dropdown-item"
                      onClick={() => handleCountrySelect(country, 'countryFrom')}
                    >
                      {country.name}
                    </div>
                  ))
                ) : null}
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="cityFrom">{t.cityFrom}</label>
          {!form.countryFrom ? (
            <input
              type="text"
              id="cityFrom"
              readOnly
              value=""
              placeholder={t.chooseCountryFirst}
              className="city-disabled"
              onFocus={(e) => e.target.blur()}
            />
          ) : countryFromId ? (
            <div className="dropdown-container" ref={cityFromDropdownRef}>
              <input
                type="text"
                id="cityFrom"
                name="cityFrom"
                value={form.cityFrom}
                onChange={(e) => {
                  handleCityChange(e, 'cityFrom');
                  if (citySearchTimeoutRef.current) clearTimeout(citySearchTimeoutRef.current);
                  citySearchTimeoutRef.current = setTimeout(() => {
                    if (showCityFromDropdown) fetchCities(countryFromId, e.target.value, 'from');
                  }, 300);
                }}
                onFocus={() => fetchCities(countryFromId, form.cityFrom, 'from')}
                onClick={() => fetchCities(countryFromId, form.cityFrom, 'from')}
                required
                placeholder={t.enterOrChooseCity}
              />
              {showCityFromDropdown && (
                <div className="dropdown-list">
                  {loadingCities ? (
                    <div className="dropdown-item">{t.loading}</div>
                  ) : cities.length > 0 ? (
                    cities.map((city) => (
                      <div
                        key={city.id}
                        className="dropdown-item"
                        onClick={() => handleCitySelect(city, 'cityFrom')}
                      >
                        {city.name}
                      </div>
                    ))
                  ) : null}
                </div>
              )}
            </div>
          ) : (
            <input
              type="text"
              id="cityFrom"
              name="cityFrom"
              value={form.cityFrom}
              onChange={(e) => handleCityChange(e, 'cityFrom')}
              required
              placeholder={t.enterCity}
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="airportFrom">{t.airportFrom}</label>
          {!form.cityFrom ? (
            <input
              type="text"
              id="airportFrom"
              readOnly
              value=""
              placeholder={t.chooseCityFirst}
              className="city-disabled"
              onFocus={(e) => e.target.blur()}
            />
          ) : cityFromId ? (
            <div className="dropdown-container" ref={airportFromDropdownRef}>
              <input
                type="text"
                id="airportFrom"
                name="airportFrom"
                value={form.airportFrom}
                onChange={(e) => {
                  handleAirportChange(e, 'airportFrom');
                  if (airportSearchTimeoutRef.current) clearTimeout(airportSearchTimeoutRef.current);
                  airportSearchTimeoutRef.current = setTimeout(() => {
                    fetchAirports(cityFromId, e.target.value, 'from');
                  }, 300);
                }}
                onFocus={() => fetchAirports(cityFromId, form.airportFrom, 'from')}
                required
                placeholder={t.enterOrChooseAirport}
              />
              {showAirportFromDropdown && (
                <div className="dropdown-list">
                  {loadingAirports ? (
                    <div className="dropdown-item">{t.loading}</div>
                  ) : airports.map((airport) => (
                    <div
                      key={airport.id}
                      className="dropdown-item"
                      onClick={() => handleAirportSelect(airport, 'airportFrom')}
                    >
                      {airport.name}{airport.iata_code ? ` (${airport.iata_code})` : ''}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <input
              type="text"
              id="airportFrom"
              name="airportFrom"
              value={form.airportFrom}
              onChange={(e) => handleAirportChange(e, 'airportFrom')}
              required
              placeholder={t.enterOrChooseAirport}
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="countryTo">{t.countryTo}</label>
          <div className="dropdown-container" ref={countryToDropdownRef}>
            <input
              type="text"
              id="countryTo"
              name="countryTo"
              value={form.countryTo}
              onChange={(e) => {
                handleCountryChange(e, 'countryTo');
                if (countrySearchTimeoutRef.current) clearTimeout(countrySearchTimeoutRef.current);
                countrySearchTimeoutRef.current = setTimeout(() => {
                  if (showCountryToDropdown) fetchCountries(e.target.value, 'to');
                }, 300);
              }}
              onFocus={() => fetchCountries(form.countryTo, 'to')}
              onClick={() => fetchCountries(form.countryTo, 'to')}
              required
              placeholder={t.enterCountry}
            />
            {showCountryToDropdown && (
              <div className="dropdown-list">
                {loadingCountries ? (
                  <div className="dropdown-item">{t.loading}</div>
                ) : countries.length > 0 ? (
                  countries.map((country) => (
                    <div
                      key={country.id}
                      className="dropdown-item"
                      onClick={() => handleCountrySelect(country, 'countryTo')}
                    >
                      {country.name}
                    </div>
                  ))
                ) : null}
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="cityTo">{t.cityTo}</label>
          {!form.countryTo ? (
            <input
              type="text"
              id="cityTo"
              readOnly
              value=""
              placeholder={t.chooseCountryFirst}
              className="city-disabled"
              onFocus={(e) => e.target.blur()}
            />
          ) : countryToId ? (
            <div className="dropdown-container" ref={cityToDropdownRef}>
              <input
                type="text"
                id="cityTo"
                name="cityTo"
                value={form.cityTo}
                onChange={(e) => {
                  handleCityChange(e, 'cityTo');
                  if (citySearchTimeoutRef.current) clearTimeout(citySearchTimeoutRef.current);
                  citySearchTimeoutRef.current = setTimeout(() => {
                    if (showCityToDropdown) fetchCities(countryToId, e.target.value, 'to');
                  }, 300);
                }}
                onFocus={() => fetchCities(countryToId, form.cityTo, 'to')}
                onClick={() => fetchCities(countryToId, form.cityTo, 'to')}
                required
                placeholder={t.enterOrChooseCity}
              />
              {showCityToDropdown && (
                <div className="dropdown-list">
                  {loadingCities ? (
                    <div className="dropdown-item">{t.loading}</div>
                  ) : cities.length > 0 ? (
                    cities.map((city) => (
                      <div
                        key={city.id}
                        className="dropdown-item"
                        onClick={() => handleCitySelect(city, 'cityTo')}
                      >
                        {city.name}
                      </div>
                    ))
                  ) : null}
                </div>
              )}
            </div>
          ) : (
            <input
              type="text"
              id="cityTo"
              name="cityTo"
              value={form.cityTo}
              onChange={(e) => handleCityChange(e, 'cityTo')}
              required
              placeholder={t.enterCity}
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="airportTo">{t.airportTo}</label>
          {!form.cityTo ? (
            <input
              type="text"
              id="airportTo"
              readOnly
              value=""
              placeholder={t.chooseCityFirst}
              className="city-disabled"
              onFocus={(e) => e.target.blur()}
            />
          ) : cityToId ? (
            <div className="dropdown-container" ref={airportToDropdownRef}>
              <input
                type="text"
                id="airportTo"
                name="airportTo"
                value={form.airportTo}
                onChange={(e) => {
                  handleAirportChange(e, 'airportTo');
                  if (airportSearchTimeoutRef.current) clearTimeout(airportSearchTimeoutRef.current);
                  airportSearchTimeoutRef.current = setTimeout(() => {
                    fetchAirports(cityToId, e.target.value, 'to');
                  }, 300);
                }}
                onFocus={() => fetchAirports(cityToId, form.airportTo, 'to')}
                required
                placeholder={t.enterOrChooseAirport}
              />
              {showAirportToDropdown && (
                <div className="dropdown-list">
                  {loadingAirports ? (
                    <div className="dropdown-item">{t.loading}</div>
                  ) : airports.map((airport) => (
                    <div
                      key={airport.id}
                      className="dropdown-item"
                      onClick={() => handleAirportSelect(airport, 'airportTo')}
                    >
                      {airport.name}{airport.iata_code ? ` (${airport.iata_code})` : ''}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <input
              type="text"
              id="airportTo"
              name="airportTo"
              value={form.airportTo}
              onChange={(e) => handleAirportChange(e, 'airportTo')}
              required
              placeholder={t.enterOrChooseAirport}
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="baggageComments">{t.baggageComments}</label>
          <input
            type="text"
            id="baggageComments"
            name="baggageComments"
            value={form.baggageComments}
            onChange={handleChange}
            placeholder={t.baggageExample}
          />
        </div>

        <button type="submit" className="submit-button">
          {t.submit}
        </button>
      </form>
    </div>
  );
}

export default App;
