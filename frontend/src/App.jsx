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

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Basic validation
    if (role === "sender") {
      if (form.dateFrom && form.dateTo && form.dateFrom > form.dateTo) {
        alert("Date from cannot be after date to");
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
                type="date"
                id="dateFrom"
                name="dateFrom"
                value={form.dateFrom}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="dateTo">Date To</label>
              <input
                type="date"
                id="dateTo"
                name="dateTo"
                value={form.dateTo}
                onChange={handleChange}
                required
                min={form.dateFrom || undefined}
              />
            </div>
          </>
        )}

        {role === "courier" && (
          <div className="form-group">
            <label htmlFor="courierDate">Date</label>
            <input
              type="date"
              id="courierDate"
              name="courierDate"
              value={form.courierDate}
              onChange={handleChange}
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
