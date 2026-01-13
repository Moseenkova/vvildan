import { useState } from 'react'
import './App.css'

function App() {
  const [role, setRole] = useState("sender");
  const [form, setForm] = useState({
    dateFrom: "",
    dateTo: "",
    courierDate: "",
    countryFrom: "",
    cityFrom: "",
    countryTo: "",
    cityTo: "",
    baggageTypes: "",
    comments: "",
  });

  // Format date to dd.mm.yyyy
  const formatDate = (value) => {
    // Remove all non-digit characters
    const digits = value.replace(/\D/g, '');
    
    // Limit to 8 digits (ddmmyyyy)
    const limited = digits.slice(0, 8);
    
    // Add dots
    if (limited.length <= 2) {
      return limited;
    } else if (limited.length <= 4) {
      return `${limited.slice(0, 2)}.${limited.slice(2)}`;
    } else {
      return `${limited.slice(0, 2)}.${limited.slice(2, 4)}.${limited.slice(4)}`;
    }
  };

  // Parse dd.mm.yyyy to Date object for validation
  const parseDate = (dateString) => {
    if (!dateString || dateString.length !== 10) return null; // dd.mm.yyyy = 10 chars
    
    const parts = dateString.split('.');
    if (parts.length !== 3) return null;
    
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed
    const year = parseInt(parts[2], 10); // Full year
    
    const date = new Date(year, month, day);
    
    // Validate the date
    if (
      date.getDate() === day &&
      date.getMonth() === month &&
      date.getFullYear() === year
    ) {
      return date;
    }
    return null;
  };

  // Validate date format (dd.mm.yyyy)
  const isValidDate = (dateString) => {
    if (!dateString || dateString.length !== 10) return false;
    return parseDate(dateString) !== null;
  };

  const handleDateChange = (e) => {
    const { name, value } = e.target;
    const formatted = formatDate(value);
    
    setForm((prev) => ({
      ...prev,
      [name]: formatted,
    }));
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate date formats
    if (role === "sender") {
      if (!isValidDate(form.dateFrom)) {
        alert("Please enter a valid date in dd.mm.yyyy format for Date From");
        return;
      }
      if (!isValidDate(form.dateTo)) {
        alert("Please enter a valid date in dd.mm.yyyy format for Date To");
        return;
      }
      
      const dateFrom = parseDate(form.dateFrom);
      const dateTo = parseDate(form.dateTo);
      
      if (dateFrom && dateTo && dateFrom > dateTo) {
        alert("Date from cannot be after date to");
        return;
      }
    } else if (role === "courier") {
      if (!isValidDate(form.courierDate)) {
        alert("Please enter a valid date in dd.mm.yyyy format");
        return;
      }
    }

    // Prepare submission data
    const submissionData = {
      role,
      ...(role === "sender" 
        ? { dateFrom: form.dateFrom, dateTo: form.dateTo }
        : { date: form.courierDate }
      ),
      countryFrom: form.countryFrom,
      cityFrom: form.cityFrom,
      countryTo: form.countryTo,
      cityTo: form.cityTo,
      baggageTypes: form.baggageTypes,
      comments: form.comments,
    };

    console.log("Form submitted:", submissionData);
    alert("Form submitted! Check console for data.");
    
    // Here you would typically send data to your backend API
  };

  return (
    <div className="app-container">
      <h1 className="app-title">Choose Your Role</h1>
      
      <div className="role-selector">
        <button
          onClick={() => setRole("sender")}
          className={`role-button ${role === "sender" ? "active" : ""}`}
        >
          Sender
        </button>
        <button
          onClick={() => setRole("courier")}
          className={`role-button ${role === "courier" ? "active" : ""}`}
        >
          Courier
        </button>
      </div>

      <form onSubmit={handleSubmit} className="order-form">
        {/* Role-dependent date fields */}
        {role === "sender" && (
          <>
            <div className="form-group">
              <label htmlFor="dateFrom">Date From</label>
              <input
                type="text"
                id="dateFrom"
                name="dateFrom"
                value={form.dateFrom}
                onChange={handleDateChange}
                placeholder="dd.mm.yyyy"
                pattern="\d{2}\.\d{2}\.\d{4}"
                maxLength={10}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="dateTo">Date To</label>
              <input
                type="text"
                id="dateTo"
                name="dateTo"
                value={form.dateTo}
                onChange={handleDateChange}
                placeholder="dd.mm.yyyy"
                pattern="\d{2}\.\d{2}\.\d{4}"
                maxLength={10}
                required
              />
            </div>
          </>
        )}

        {role === "courier" && (
          <div className="form-group">
            <label htmlFor="courierDate">Date</label>
            <input
              type="text"
              id="courierDate"
              name="courierDate"
              value={form.courierDate}
              onChange={handleDateChange}
              placeholder="dd.mm.yyyy"
              pattern="\d{2}\.\d{2}\.\d{4}"
              maxLength={10}
              required
            />
          </div>
        )}

        {/* Common fields */}
        <div className="form-group">
          <label htmlFor="countryFrom">Country From</label>
          <input
            type="text"
            id="countryFrom"
            name="countryFrom"
            value={form.countryFrom}
            onChange={handleChange}
            required
            placeholder="Enter country"
          />
        </div>

        <div className="form-group">
          <label htmlFor="cityFrom">City From</label>
          <input
            type="text"
            id="cityFrom"
            name="cityFrom"
            value={form.cityFrom}
            onChange={handleChange}
            required
            placeholder="Enter city"
          />
        </div>

        <div className="form-group">
          <label htmlFor="countryTo">Country To</label>
          <input
            type="text"
            id="countryTo"
            name="countryTo"
            value={form.countryTo}
            onChange={handleChange}
            required
            placeholder="Enter country"
          />
        </div>

        <div className="form-group">
          <label htmlFor="cityTo">City To</label>
          <input
            type="text"
            id="cityTo"
            name="cityTo"
            value={form.cityTo}
            onChange={handleChange}
            required
            placeholder="Enter city"
          />
        </div>

        <div className="form-group">
          <label htmlFor="baggageTypes">Baggage Types</label>
          <input
            type="text"
            id="baggageTypes"
            name="baggageTypes"
            value={form.baggageTypes}
            onChange={handleChange}
            placeholder="e.g. Small bag, Box, Fragile"
          />
        </div>

        <div className="form-group">
          <label htmlFor="comments">Comments</label>
          <textarea
            id="comments"
            name="comments"
            value={form.comments}
            onChange={handleChange}
            rows={4}
            placeholder="Additional comments or special instructions"
          />
        </div>

        <button type="submit" className="submit-button">
          Submit
        </button>
      </form>
    </div>
  );
}

export default App;
