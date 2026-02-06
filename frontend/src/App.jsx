import { useState, useEffect, useRef } from 'react'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import './App.css'

function App() {
  const getTelegramUserId = () => {
    try {
      const tg = window?.Telegram?.WebApp;
      const id = tg?.initDataUnsafe?.user?.id;
      // return typeof id === 'number' ? id : null;
      return typeof id === 'number' ? id : 5875912525;
    } catch {
      return null;
    }
  };

  const [role, setRole] = useState("sender");
  const [form, setForm] = useState({
    dateFrom: null,
    dateTo: null,
    courierDate: null,
    countryFrom: "",
    cityFrom: "",
    countryTo: "",
    cityTo: "",
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

  // City dropdown state
  const [cities, setCities] = useState([]);
  const [showCityFromDropdown, setShowCityFromDropdown] = useState(false);
  const [showCityToDropdown, setShowCityToDropdown] = useState(false);
  const [loadingCities, setLoadingCities] = useState(false);
  const cityFromDropdownRef = useRef(null);
  const cityToDropdownRef = useRef(null);
  const citySearchTimeoutRef = useRef(null);

  // City IDs when selected from dropdown (null if typed manually)
  const [cityFromId, setCityFromId] = useState(null);
  const [cityToId, setCityToId] = useState(null);
  const [submitStatus, setSubmitStatus] = useState(null); // 'idle' | 'loading' | 'success' | 'error'

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
      const response = await fetch(`http://localhost:8001/api/countries?q=${q}`);
      if (response.ok) {
        const data = await response.json();
        setCountries(Array.isArray(data) ? data : []);
      } else {
        setCountries([]);
        console.error('Failed to fetch countries');
      }
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
    }));
    if (field === 'countryFrom') {
      setCountryFromId(countryId);
      setCityFromId(null);
      setShowCountryFromDropdown(false);
    } else {
      setCountryToId(countryId);
      setCityToId(null);
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
      const response = await fetch(`http://localhost:8001/api/cities?country_id=${countryId}&q=${q}`);
      if (response.ok) {
        const data = await response.json();
        setCities(Array.isArray(data) ? data : []);
      } else {
        setCities([]);
      }
    } catch (error) {
      setCities([]);
      console.error('Error fetching cities:', error);
    } finally {
      setLoadingCities(false);
    }
  };

  const handleCitySelect = (city, field) => {
    const cityName = typeof city === 'string' ? city : city.name;
    const cityId = typeof city === 'object' ? city.id : null;
    setForm((prev) => ({
      ...prev,
      [field]: cityName,
    }));
    if (field === 'cityFrom') {
      setCityFromId(cityId);
      setShowCityFromDropdown(false);
    } else {
      setCityToId(cityId);
      setShowCityToDropdown(false);
    }
  };

  // Clear countryId when user types in country field (manual input)
  const handleCountryChange = (e, field) => {
    handleChange(e);
    if (field === 'countryFrom') {
      setCountryFromId(null);
      setCityFromId(null);
    } else {
      setCountryToId(null);
      setCityToId(null);
    }
  };

  // Clear cityId when user types in city field (manual input)
  const handleCityChange = (e, field) => {
    handleChange(e);
    if (field === 'cityFrom') setCityFromId(null);
    else setCityToId(null);
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
    };

    if (showCountryFromDropdown || showCountryToDropdown || showCityFromDropdown || showCityToDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showCountryFromDropdown, showCountryToDropdown, showCityFromDropdown, showCityToDropdown]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate dates
    if (role === "sender") {
      if (!form.dateFrom) {
        alert("Please select a date for Date From");
        return;
      }
      if (!form.dateTo) {
        alert("Please select a date for Date To");
        return;
      }
      
      if (form.dateFrom > form.dateTo) {
        alert("Date from cannot be after date to");
        return;
      }
    } else if (role === "courier") {
      if (!form.courierDate) {
        alert("Please select a date");
        return;
      }
    }

    const payload = {
      role,
      ...(role === "sender" 
        ? { 
            date_from: formatDateToString(form.dateFrom), 
            date_to: formatDateToString(form.dateTo),
            date: null
          }
        : { 
            date: formatDateToString(form.courierDate),
            date_from: null,
            date_to: null
          }
      ),
      country_from: { id: countryFromId, name: form.countryFrom },
      city_from: { id: cityFromId, name: form.cityFrom },
      country_to: { id: countryToId, name: form.countryTo },
      city_to: { id: cityToId, name: form.cityTo },
      comment: form.baggageComments || "",
      telegram_id: getTelegramUserId(),
    };

    setSubmitStatus('loading');
    try {
      const response = await fetch('http://localhost:8001/api/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        setSubmitStatus('success');
        alert("Заявка успешно отправлена!");
      } else {
        const err = await response.json().catch(() => ({}));
        setSubmitStatus('error');
        alert(err.detail || `Ошибка: ${response.status}`);
      }
    } catch (error) {
      setSubmitStatus('error');
      alert("Ошибка сети: " + error.message);
    }
  };

  return (
    <div className="app-container">
      <div className="role-selector">
        <button
          onClick={() => setRole("sender")}
          className={`role-button ${role === "sender" ? "active" : ""}`}
        >
          Отправитель
        </button>
        <button
          onClick={() => setRole("courier")}
          className={`role-button ${role === "courier" ? "active" : ""}`}
        >
          Курьер
        </button>
      </div>

      <form onSubmit={handleSubmit} className="order-form">
        {/* Role-dependent date fields */}
        {role === "sender" && (
          <>
            <div className="form-group">
              <label htmlFor="dateFrom">В период с даты</label>
              <DatePicker
                id="dateFrom"
                selected={form.dateFrom}
                onChange={(date) => handleDateChange(date, 'dateFrom')}
                dateFormat="dd.MM.yyyy"
                placeholderText="дд.мм.гггг"
                className="date-picker-input"
                required
                minDate={new Date()}
              />
            </div>
            <div className="form-group">
              <label htmlFor="dateTo">До даты</label>
              <DatePicker
                id="dateTo"
                selected={form.dateTo}
                onChange={(date) => handleDateChange(date, 'dateTo')}
                dateFormat="dd.MM.yyyy"
                placeholderText="дд.мм.гггг"
                className="date-picker-input"
                required
                minDate={form.dateFrom || new Date()}
              />
            </div>
          </>
        )}

        {role === "courier" && (
          <div className="form-group">
            <label htmlFor="courierDate">Дата</label>
            <DatePicker
              id="courierDate"
              selected={form.courierDate}
              onChange={(date) => handleDateChange(date, 'courierDate')}
              dateFormat="dd.MM.yyyy"
              placeholderText="дд.мм.гггг"
              className="date-picker-input"
              required
              minDate={new Date()}
            />
          </div>
        )}

        {/* Common fields */}
        <div className="form-group">
          <label htmlFor="countryFrom">Страна отправления</label>
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
              placeholder="Введите страну"
            />
            {showCountryFromDropdown && (
              <div className="dropdown-list">
                {loadingCountries ? (
                  <div className="dropdown-item">Загрузка...</div>
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
          <label htmlFor="cityFrom">Город отправления</label>
          {!form.countryFrom ? (
            <input
              type="text"
              id="cityFrom"
              readOnly
              value=""
              placeholder="Сначала выберите страну"
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
                placeholder="Введите или выберите город"
              />
              {showCityFromDropdown && (
                <div className="dropdown-list">
                  {loadingCities ? (
                    <div className="dropdown-item">Загрузка...</div>
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
              onChange={handleChange}
              required
              placeholder="Введите город"
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="countryTo">Страна прибытия</label>
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
              placeholder="Введите страну"
            />
            {showCountryToDropdown && (
              <div className="dropdown-list">
                {loadingCountries ? (
                  <div className="dropdown-item">Загрузка...</div>
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
          <label htmlFor="cityTo">Город прибытия</label>
          {!form.countryTo ? (
            <input
              type="text"
              id="cityTo"
              readOnly
              value=""
              placeholder="Сначала выберите страну"
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
                placeholder="Введите или выберите город"
              />
              {showCityToDropdown && (
                <div className="dropdown-list">
                  {loadingCities ? (
                    <div className="dropdown-item">Загрузка...</div>
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
              onChange={handleChange}
              required
              placeholder="Введите город"
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="baggageComments">Комментарий к багажу</label>
          <input
            type="text"
            id="baggageComments"
            name="baggageComments"
            value={form.baggageComments}
            onChange={handleChange}
            placeholder="Например: Одежда 5 кг, Документы, Электроника"
          />
        </div>

        <button type="submit" className="submit-button" disabled={submitStatus === 'loading'}>
          {submitStatus === 'loading' ? 'Отправка...' : 'Отправить заявку'}
        </button>
      </form>
    </div>
  );
}

export default App;
