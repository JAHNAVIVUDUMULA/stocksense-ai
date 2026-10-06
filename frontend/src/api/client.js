// StockSense AI - Central API Client

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

class ApiClient {
  constructor() {
    this.baseUrl = BASE_URL;
  }

  getToken() {
    return localStorage.getItem("stocksense_token");
  }

  setToken(token) {
    if (token) {
      localStorage.setItem("stocksense_token", token);
    } else {
      localStorage.removeItem("stocksense_token");
    }
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers = {
      ...(options.headers || {}),
    };

    // If body is NOT FormData, set application/json
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // Handle plain text response (like CSV download)
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("text/plain")) {
        return await response.text();
      }

      const data = await response.json();

      if (!response.ok) {
        const errorMsg = data?.detail || data?.message || "An unexpected error occurred.";
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, err.message);
      throw err;
    }
  }

  get(endpoint, params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        query.append(k, v);
      }
    });
    const queryString = query.toString() ? `?${query.toString()}` : "";
    return this.request(`${endpoint}${queryString}`, { method: "GET" });
  }

  post(endpoint, body) {
    return this.request(endpoint, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  put(endpoint, body = {}) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  }
}

export const api = new ApiClient();
export default api;
