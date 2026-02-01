import { useState, useEffect, useRef } from 'react'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import './App.css'

function App() {
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
      const response = await fetch(`http://localhost:8000/api/countries?q=${q}`);
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

  const handleCountrySelect = (countryName, field) => {
    setForm((prev) => ({
      ...prev,
      [field]: countryName,
    }));
    if (field === 'countryFrom') setShowCountryFromDropdown(false);
    else setShowCountryToDropdown(false);
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
    };

    if (showCountryFromDropdown || showCountryToDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showCountryFromDropdown, showCountryToDropdown]);

  const handleSubmit = (e) => {
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
      countryTo: form.countryTo,
      cityTo: form.cityTo,
      baggageComments: form.baggageComments,
    };

    console.log("Form submitted:", submissionData);
    alert("Form submitted! Check console for data.");
    
    // Here you would typically send data to your backend API
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
                handleChange(e);
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
                      onClick={() => handleCountrySelect(country.name, 'countryFrom')}
                    >
                      {country.name}
                    </div>
                  ))
                ) : (
                  <div className="dropdown-item">Нет стран</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="cityFrom">Город отправления</label>
          <input
            type="text"
            id="cityFrom"
            name="cityFrom"
            value={form.cityFrom}
            onChange={handleChange}
            required
            placeholder="Введите город"
          />
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
                handleChange(e);
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
                      onClick={() => handleCountrySelect(country.name, 'countryTo')}
                    >
                      {country.name}
                    </div>
                  ))
                ) : (
                  <div className="dropdown-item">Нет стран</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="cityTo">Город прибытия</label>
          <input
            type="text"
            id="cityTo"
            name="cityTo"
            value={form.cityTo}
            onChange={handleChange}
            required
            placeholder="Введите город"
          />
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

        <button type="submit" className="submit-button">
          Отправить заявку
        </button>
      </form>
    </div>
  );
}

export default App;
