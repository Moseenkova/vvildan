import axios from "axios";

// Determine base URL depending on env, if using Vite proxy it's just /
const API_URL = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Important for sending/receiving cookies (refresh token)
});

// Request interceptor to add the access token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle 401 and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If the error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Attempt to refresh token using the refresh cookie
        const { data } = await axios.post(`${API_URL}/auth/refresh`, {}, { withCredentials: true });

        // Save new access token
        localStorage.setItem("access_token", data.access_token);

        // Update header and retry original request
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // If refresh fails (e.g. invalid refresh token), user must login again
        localStorage.removeItem("access_token");
        // We could emit an event here to notify the app to show a login screen or redirect
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
