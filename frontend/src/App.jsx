import { useEffect, useState } from "react";
import api from "./api/client";
import "./App.css";

function RiskBadge({ risk }) {
  const value = risk || "LOW";

  return (
    <span className={`risk-badge ${value.toLowerCase()}`}>
      {value}
    </span>
  );
}

function StatCard({ title, value, subtitle, icon, danger }) {
  return (
    <div className={`stat-card ${danger ? "danger-card" : ""}`}>
      <div className="stat-icon">{icon}</div>

      <div>
        <p>{title}</p>
        <h2>{value}</h2>
        {subtitle && <span>{subtitle}</span>}
      </div>
    </div>
  );
}

function Loading() {
  return (
    <div className="loading">
      <div className="loader"></div>
      <p>Loading StockSense AI...</p>
    </div>
  );
}

function ErrorBox({ message, onRetry }) {
  return (
    <div className="error-box">
      <h3>Backend connection problem</h3>
      <p>{message}</p>

      <button onClick={onRetry}>Retry</button>
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="empty-state">
      <span>✓</span>
      <p>{message}</p>
    </div>
  );
}

/*
 * ---------------------------------------------------------
 * FORMAT AI EXPLANATION SAFELY
 * ---------------------------------------------------------
 */

function formatExplanation(explainability) {
  if (!explainability) {
    return "The AI prediction is based on the available inventory and sales data.";
  }

  if (typeof explainability === "string") {
    return explainability;
  }

  if (Array.isArray(explainability)) {
    return explainability
      .map((item) =>
        typeof item === "object"
          ? JSON.stringify(item)
          : String(item)
      )
      .join(" ");
  }

  if (typeof explainability === "object") {
    return Object.entries(explainability)
      .map(([key, value]) => {
        const label = key
          .replace(/_/g, " ")
          .replace(/\b\w/g, (letter) => letter.toUpperCase());

        let formattedValue = value;

        if (typeof value === "object") {
          formattedValue = JSON.stringify(value);
        }

        return `${label}: ${formattedValue}`;
      })
      .join(" • ");
  }

  return String(explainability);
}

function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  const [analytics, setAnalytics] = useState(null);
  const [products, setProducts] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [loading, setLoading] = useState(true);
  const [pageLoading, setPageLoading] = useState(false);

  const [error, setError] = useState("");

  const [productSearch, setProductSearch] = useState("");
  const [productFilter, setProductFilter] = useState("all");
  const [productSort, setProductSort] = useState("risk");

  const [notificationOpen, setNotificationOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  /*
   * ---------------------------------------------------------
   * LOAD DASHBOARD DATA
   * ---------------------------------------------------------
   */

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const [
        analyticsData,
        productsData,
        alertsData,
      ] = await Promise.all([
        api.get("/analytics"),
        api.get("/products", {
          filter_by: "all",
          sort_by: "risk",
        }),
        api.get("/alerts"),
      ]);

      setAnalytics(analyticsData);
      setProducts(productsData || []);
      setAlerts(alertsData || []);
    } catch (err) {
      console.error("Dashboard error:", err);

      setError(
        err.message ||
          "Unable to connect to StockSense backend. Make sure the backend is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  };

  /*
   * ---------------------------------------------------------
   * LOAD PRODUCTS
   * ---------------------------------------------------------
   */

  const loadProducts = async () => {
    try {
      setPageLoading(true);
      setError("");

      const data = await api.get("/products", {
        search: productSearch,
        filter_by: productFilter,
        sort_by: productSort,
      });

      setProducts(data || []);
    } catch (err) {
      console.error("Products error:", err);

      setError(err.message || "Unable to load products.");
    } finally {
      setPageLoading(false);
    }
  };

  /*
   * ---------------------------------------------------------
   * LOAD PREDICTIONS
   * ---------------------------------------------------------
   */

  const loadPredictions = async () => {
    try {
      setPageLoading(true);
      setError("");

      const data = await api.get("/predictions");

      /*
       * Make sure predictions is always an array.
       * This prevents the page from crashing if the backend
       * returns an unexpected response structure.
       */
      if (Array.isArray(data)) {
        setPredictions(data);
      } else if (Array.isArray(data?.predictions)) {
        setPredictions(data.predictions);
      } else {
        setPredictions([]);
      }
    } catch (err) {
      console.error("Predictions error:", err);

      setError(err.message || "Unable to load predictions.");
    } finally {
      setPageLoading(false);
    }
  };

  /*
   * ---------------------------------------------------------
   * LOAD ALERTS
   * ---------------------------------------------------------
   */

  const loadAlerts = async () => {
    try {
      setPageLoading(true);
      setError("");

      const data = await api.get("/alerts");

      setAlerts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Alerts error:", err);

      setError(err.message || "Unable to load alerts.");
    } finally {
      setPageLoading(false);
    }
  };

  /*
   * ---------------------------------------------------------
   * LOAD ANALYTICS
   * ---------------------------------------------------------
   */

  const loadAnalytics = async () => {
    try {
      setPageLoading(true);
      setError("");

      const data = await api.get("/analytics");

      setAnalytics(data);
    } catch (err) {
      console.error("Analytics error:", err);

      setError(err.message || "Unable to load analytics.");
    } finally {
      setPageLoading(false);
    }
  };

  /*
   * ---------------------------------------------------------
   * INITIAL LOAD
   * ---------------------------------------------------------
   */

  useEffect(() => {
    loadDashboard();
  }, []);

  /*
   * ---------------------------------------------------------
   * PAGE NAVIGATION
   * ---------------------------------------------------------
   */

  const handlePageChange = async (page) => {
    setActivePage(page);
    setNotificationOpen(false);
    setError("");

    if (page === "Dashboard") {
      await loadDashboard();
    }

    if (page === "Products") {
      await loadProducts();
    }

    if (page === "Predictions") {
      await loadPredictions();
    }

    if (page === "Alerts") {
      await loadAlerts();
    }

    if (page === "Analytics") {
      await loadAnalytics();
    }
  };

  /*
   * ---------------------------------------------------------
   * ALERT ACTIONS
   * ---------------------------------------------------------
   */

  const markAlertRead = async (id) => {
    try {
      await api.put(`/alerts/${id}/read`);

      await loadAlerts();

      if (activePage === "Dashboard") {
        await loadDashboard();
      }
    } catch (err) {
      console.error("Mark alert read error:", err);
    }
  };

  const markAllAlertsRead = async () => {
    try {
      await api.put("/alerts/mark-all-read");

      await loadAlerts();

      if (activePage === "Dashboard") {
        await loadDashboard();
      }
    } catch (err) {
      console.error("Mark all alerts error:", err);
    }
  };

  /*
   * ---------------------------------------------------------
   * NOTIFICATION COUNT
   * ---------------------------------------------------------
   */

  const unreadAlerts = alerts.filter(
    (alert) => !alert.is_read
  );

  /*
   * ---------------------------------------------------------
   * DASHBOARD
   * ---------------------------------------------------------
   */

  const renderDashboard = () => {
    if (loading) {
      return <Loading />;
    }

    if (error) {
      return (
        <ErrorBox
          message={error}
          onRetry={loadDashboard}
        />
      );
    }

    const summary = analytics?.summary;

    return (
      <>
        <div className="page-heading">
          <div>
            <h1>Dashboard</h1>
            <p>AI-powered inventory intelligence</p>
          </div>

          <button
            className="refresh-btn"
            onClick={loadDashboard}
          >
            ↻ Refresh
          </button>
        </div>

        <div className="stats-grid">
          <StatCard
            title="Total Products"
            value={summary?.total_products ?? 0}
            subtitle="Products being monitored"
            icon="📦"
          />

          <StatCard
            title="Low Stock"
            value={summary?.low_stock_products ?? 0}
            subtitle="Need attention"
            icon="⚠️"
            danger={summary?.low_stock_products > 0}
          />

          <StatCard
            title="High Risk"
            value={summary?.high_risk_products ?? 0}
            subtitle="AI detected risk"
            icon="📈"
            danger={summary?.high_risk_products > 0}
          />

          <StatCard
            title="Critical"
            value={summary?.critical_risk_products ?? 0}
            subtitle="Immediate action"
            icon="🚨"
            danger={summary?.critical_risk_products > 0}
          />
        </div>

        <div className="stats-grid secondary-stats">
          <StatCard
            title="Stockout Soon"
            value={summary?.stockout_soon_products ?? 0}
            subtitle="Within 7 days"
            icon="⏳"
          />

          <StatCard
            title="Restock Recommendations"
            value={
              summary?.pending_restock_recommendations ?? 0
            }
            subtitle="AI recommendations"
            icon="🔄"
          />

          <StatCard
            title="Units Sold"
            value={summary?.total_units_sold ?? 0}
            subtitle="Recorded sales"
            icon="🛒"
          />

          <StatCard
            title="Total Revenue"
            value={`₹${Number(
              summary?.total_revenue ?? 0
            ).toLocaleString()}`}
            subtitle="Recorded revenue"
            icon="💰"
          />
        </div>

        <div className="dashboard-grid">
          <section className="panel urgent-panel">
            <div className="panel-header">
              <div>
                <h2>🚨 Products Requiring Attention</h2>

                <p>
                  AI identified these as the most urgent
                  products
                </p>
              </div>
            </div>

            {analytics?.urgent_products?.length ? (
              <div className="urgent-list">
                {analytics.urgent_products
                  .slice(0, 6)
                  .map((product) => (
                    <div
                      className="urgent-item"
                      key={product.id}
                    >
                      <div className="product-main">
                        <div className="product-avatar">
                          {product.name
                            ?.charAt(0)
                            ?.toUpperCase()}
                        </div>

                        <div>
                          <strong>{product.name}</strong>

                          <span>
                            {product.sku} ·{" "}
                            {product.category}
                          </span>
                        </div>
                      </div>

                      <div className="stock-info">
                        <span>Stock</span>

                        <strong>
                          {product.current_stock}
                        </strong>
                      </div>

                      <div className="stockout-info">
                        <span>Stockout</span>

                        <strong>
                          {product.predicted_stockout_days !=
                          null
                            ? `${Math.round(
                                product.predicted_stockout_days
                              )} days`
                            : "—"}
                        </strong>
                      </div>

                      <RiskBadge
                        risk={product.risk_level}
                      />
                    </div>
                  ))}
              </div>
            ) : (
              <EmptyState message="No urgent products detected." />
            )}
          </section>

          <section className="panel alerts-panel">
            <div className="panel-header">
              <div>
                <h2>🔔 Recent Alerts</h2>

                <p>
                  {unreadAlerts.length} unread alerts
                </p>
              </div>

              {unreadAlerts.length > 0 && (
                <button
                  className="small-btn"
                  onClick={markAllAlertsRead}
                >
                  Mark all read
                </button>
              )}
            </div>

            {alerts.length ? (
              <div className="alert-list">
                {alerts.slice(0, 5).map((alert) => (
                  <div
                    className={`alert-item ${
                      alert.is_read ? "read" : ""
                    }`}
                    key={alert.id}
                  >
                    <div
                      className={`alert-dot ${
                        alert.severity?.toLowerCase()
                      }`}
                    />

                    <div className="alert-content">
                      <strong>
                        {alert.product_name}
                      </strong>

                      <p>{alert.message}</p>

                      <span>
                        {alert.recommended_action}
                      </span>
                    </div>

                    {!alert.is_read && (
                      <button
                        className="read-btn"
                        onClick={() =>
                          markAlertRead(alert.id)
                        }
                      >
                        Read
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="No alerts right now." />
            )}
          </section>
        </div>

        <section className="panel products-panel">
          <div className="panel-header">
            <div>
              <h2>📦 Inventory Overview</h2>

              <p>Products sorted by AI risk</p>
            </div>

            <button
              className="small-btn"
              onClick={() =>
                handlePageChange("Products")
              }
            >
              View all
            </button>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Stock</th>
                  <th>Daily Demand</th>
                  <th>Stockout</th>
                  <th>Risk</th>
                  <th>Restock</th>
                </tr>
              </thead>

              <tbody>
                {products.slice(0, 8).map((product) => (
                  <tr key={product.id}>
                    <td>
                      <strong>{product.name}</strong>

                      <small>{product.sku}</small>
                    </td>

                    <td>{product.category}</td>

                    <td>
                      <strong>
                        {product.current_stock}
                      </strong>

                      <small>
                        Min: {product.minimum_stock}
                      </small>
                    </td>

                    <td>
                      {product.prediction
                        ? Number(
                            product.prediction
                              .predicted_daily_demand
                          ).toFixed(1)
                        : "—"}
                    </td>

                    <td>
                      {product.prediction
                        ?.days_until_stockout != null
                        ? `${Math.round(
                            product.prediction
                              .days_until_stockout
                          )} days`
                        : "—"}
                    </td>

                    <td>
                      <RiskBadge
                        risk={
                          product.prediction?.risk_level
                        }
                      />
                    </td>

                    <td>
                      {product.prediction
                        ?.recommended_restock ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </>
    );
  };

  /*
   * ---------------------------------------------------------
   * PRODUCTS PAGE
   * ---------------------------------------------------------
   */

  const renderProducts = () => {
    if (pageLoading) {
      return <Loading />;
    }

    if (error) {
      return (
        <ErrorBox
          message={error}
          onRetry={loadProducts}
        />
      );
    }

    return (
      <>
        <div className="page-heading">
          <div>
            <h1>Products</h1>

            <p>
              Monitor inventory and AI stockout risk
            </p>
          </div>

          <button
            className="refresh-btn"
            onClick={loadProducts}
          >
            ↻ Refresh
          </button>
        </div>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>📦 Product Inventory</h2>

              <p>{products.length} products found</p>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
              marginBottom: "20px",
            }}
          >
            <input
              className="form-control"
              style={{
                maxWidth: "320px",
              }}
              value={productSearch}
              onChange={(e) =>
                setProductSearch(e.target.value)
              }
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  loadProducts();
                }
              }}
              placeholder="Search product, SKU or category..."
            />

            <select
              className="form-control"
              style={{
                maxWidth: "190px",
              }}
              value={productFilter}
              onChange={(e) =>
                setProductFilter(e.target.value)
              }
            >
              <option value="all">All Products</option>

              <option value="in_stock">In Stock</option>

              <option value="low_stock">Low Stock</option>

              <option value="high_risk">High Risk</option>

              <option value="critical">Critical</option>

              <option value="out_of_stock">
                Out of Stock
              </option>
            </select>

            <select
              className="form-control"
              style={{
                maxWidth: "190px",
              }}
              value={productSort}
              onChange={(e) =>
                setProductSort(e.target.value)
              }
            >
              <option value="risk">Sort by Risk</option>

              <option value="stock_asc">
                Stock: Low to High
              </option>

              <option value="stock_desc">
                Stock: High to Low
              </option>

              <option value="demand">
                Highest Demand
              </option>

              <option value="soonest">
                Soonest Stockout
              </option>

              <option value="name">
                Product Name
              </option>
            </select>

            <button
              className="refresh-btn"
              onClick={loadProducts}
            >
              Apply
            </button>
          </div>

          {products.length === 0 ? (
            <EmptyState message="No products found." />
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Category</th>
                    <th>SKU</th>
                    <th>Current Stock</th>
                    <th>Daily Demand</th>
                    <th>Stockout</th>
                    <th>Risk</th>
                    <th>Restock</th>
                  </tr>
                </thead>

                <tbody>
                  {products.map((product) => (
                    <tr key={product.id}>
                      <td>
                        <strong>{product.name}</strong>

                        <small>
                          {product.supplier_name ||
                            "Supplier not specified"}
                        </small>
                      </td>

                      <td>{product.category}</td>

                      <td>{product.sku}</td>

                      <td>
                        <strong>
                          {product.current_stock}
                        </strong>

                        <small>
                          Min: {product.minimum_stock}
                        </small>
                      </td>

                      <td>
                        {product.prediction
                          ? Number(
                              product.prediction
                                .predicted_daily_demand
                            ).toFixed(1)
                          : "—"}
                      </td>

                      <td>
                        {product.prediction
                          ?.days_until_stockout != null
                          ? `${Math.round(
                              product.prediction
                                .days_until_stockout
                            )} days`
                          : "—"}
                      </td>

                      <td>
                        <RiskBadge
                          risk={
                            product.prediction?.risk_level
                          }
                        />
                      </td>

                      <td>
                        {product.prediction
                          ?.recommended_restock ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </>
    );
  };

  /*
   * ---------------------------------------------------------
   * PREDICTIONS PAGE
   * ---------------------------------------------------------
   */

  const renderPredictions = () => {
    if (pageLoading) {
      return <Loading />;
    }

    if (error) {
      return (
        <ErrorBox
          message={error}
          onRetry={loadPredictions}
        />
      );
    }

    return (
      <>
        <div className="page-heading">
          <div>
            <h1>AI Predictions</h1>

            <p>
              Predict when products may run out of stock
            </p>
          </div>

          <button
            className="refresh-btn"
            onClick={loadPredictions}
          >
            ↻ Refresh
          </button>
        </div>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>🧠 Stockout Predictions</h2>

              <p>
                AI-generated demand and stockout forecasts
              </p>
            </div>
          </div>

          {predictions.length === 0 ? (
            <EmptyState message="No predictions available." />
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Current Stock</th>
                    <th>Daily Demand</th>
                    <th>Stockout Date</th>
                    <th>Days Left</th>
                    <th>Risk</th>
                    <th>Confidence</th>
                    <th>Recommended Restock</th>
                  </tr>
                </thead>

                <tbody>
                  {predictions.map((prediction) => (
                    <tr key={prediction.id}>
                      <td>
                        <strong>
                          {prediction.product_name}
                        </strong>

                        <small>
                          {prediction.product_sku}
                        </small>
                      </td>

                      <td>
                        {prediction.current_stock}
                      </td>

                      <td>
                        {prediction.predicted_daily_demand !=
                        null
                          ? Number(
                              prediction.predicted_daily_demand
                            ).toFixed(1)
                          : "—"}
                      </td>

                      <td>
                        {prediction.predicted_stockout_date ||
                          "—"}
                      </td>

                      <td>
                        {prediction.days_until_stockout !=
                        null
                          ? `${Math.round(
                              prediction.days_until_stockout
                            )} days`
                          : "—"}
                      </td>

                      <td>
                        <RiskBadge
                          risk={prediction.risk_level}
                        />
                      </td>

                      <td>
                        {prediction.confidence_label ||
                          (prediction.confidence != null
                            ? `${Math.round(
                                prediction.confidence * 100
                              )}%`
                            : "—")}
                      </td>

                      <td>
                        <strong>
                          {prediction.recommended_restock ??
                            0}
                        </strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {predictions.length > 0 && (
          <div className="dashboard-grid">
            {predictions
              .filter(
                (prediction) =>
                  prediction.risk_level === "CRITICAL" ||
                  prediction.risk_level === "HIGH"
              )
              .slice(0, 4)
              .map((prediction) => (
                <section
                  className="panel"
                  key={`explain-${prediction.id}`}
                >
                  <div className="panel-header">
                    <div>
                      <h2>
                        {prediction.product_name}
                      </h2>

                      <p>
                        AI prediction explanation
                      </p>
                    </div>

                    <RiskBadge
                      risk={prediction.risk_level}
                    />
                  </div>

                  <p>
                    {prediction.explanation_summary ||
                      formatExplanation(
                        prediction.explainability
                      )}
                  </p>

                  <div
                    style={{
                      marginTop: "14px",
                      display: "grid",
                      gap: "8px",
                    }}
                  >
                    <div>
                      <strong>Model:</strong>{" "}
                      {prediction.model_used || "—"}
                    </div>

                    <div>
                      <strong>
                        Lead-time demand:
                      </strong>{" "}
                      {prediction.lead_time_demand ?? "—"}
                    </div>

                    <div>
                      <strong>Safety stock:</strong>{" "}
                      {prediction.safety_stock ?? "—"}
                    </div>

                    <div>
                      <strong>Reorder point:</strong>{" "}
                      {prediction.reorder_point ?? "—"}
                    </div>
                  </div>
                </section>
              ))}
          </div>
        )}
      </>
    );
  };

  /*
   * ---------------------------------------------------------
   * ALERTS PAGE
   * ---------------------------------------------------------
   */

  const renderAlerts = () => {
    if (pageLoading) {
      return <Loading />;
    }

    if (error) {
      return (
        <ErrorBox
          message={error}
          onRetry={loadAlerts}
        />
      );
    }

    return (
      <>
        <div className="page-heading">
          <div>
            <h1>Alerts</h1>

            <p>
              Inventory warnings and AI restock
              recommendations
            </p>
          </div>

          <div
            style={{
              display: "flex",
              gap: "10px",
            }}
          >
            {unreadAlerts.length > 0 && (
              <button
                className="refresh-btn"
                onClick={markAllAlertsRead}
              >
                Mark all read
              </button>
            )}

            <button
              className="refresh-btn"
              onClick={loadAlerts}
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>🔔 Inventory Alerts</h2>

              <p>
                {alerts.length} total alerts ·{" "}
                {unreadAlerts.length} unread
              </p>
            </div>
          </div>

          {alerts.length === 0 ? (
            <EmptyState message="No alerts right now." />
          ) : (
            <div className="alert-list">
              {alerts.map((alert) => (
                <div
                  className={`alert-item ${
                    alert.is_read ? "read" : ""
                  }`}
                  key={alert.id}
                >
                  <div
                    className={`alert-dot ${
                      alert.severity?.toLowerCase()
                    }`}
                  />

                  <div className="alert-content">
                    <strong>
                      {alert.product_name}
                    </strong>

                    <p>{alert.message}</p>

                    <span>
                      {alert.recommended_action}
                    </span>

                    <small>
                      Severity: {alert.severity || "—"} ·{" "}
                      {alert.alert_type || "—"}
                    </small>
                  </div>

                  {!alert.is_read && (
                    <button
                      className="read-btn"
                      onClick={() =>
                        markAlertRead(alert.id)
                      }
                    >
                      Mark read
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </>
    );
  };

  /*
   * ---------------------------------------------------------
   * ANALYTICS PAGE
   * ---------------------------------------------------------
   */

  const renderAnalytics = () => {
    if (pageLoading) {
      return <Loading />;
    }

    if (error) {
      return (
        <ErrorBox
          message={error}
          onRetry={loadAnalytics}
        />
      );
    }

    const summary = analytics?.summary;

    return (
      <>
        <div className="page-heading">
          <div>
            <h1>Analytics</h1>

            <p>
              Inventory and sales intelligence
            </p>
          </div>

          <button
            className="refresh-btn"
            onClick={loadAnalytics}
          >
            ↻ Refresh
          </button>
        </div>

        <div className="stats-grid">
          <StatCard
            title="Total Products"
            value={summary?.total_products ?? 0}
            subtitle="Products monitored"
            icon="📦"
          />

          <StatCard
            title="Low Stock"
            value={summary?.low_stock_products ?? 0}
            subtitle="Below minimum stock"
            icon="⚠️"
          />

          <StatCard
            title="High Risk"
            value={summary?.high_risk_products ?? 0}
            subtitle="AI risk detected"
            icon="📈"
          />

          <StatCard
            title="Critical Risk"
            value={summary?.critical_risk_products ?? 0}
            subtitle="Immediate attention"
            icon="🚨"
            danger={
              summary?.critical_risk_products > 0
            }
          />
        </div>

        <div className="stats-grid secondary-stats">
          <StatCard
            title="Stockout Soon"
            value={
              summary?.stockout_soon_products ?? 0
            }
            subtitle="Within 7 days"
            icon="⏳"
          />

          <StatCard
            title="Restock Needed"
            value={
              summary?.pending_restock_recommendations ??
              0
            }
            subtitle="AI recommendations"
            icon="🔄"
          />

          <StatCard
            title="Units Sold"
            value={summary?.total_units_sold ?? 0}
            subtitle="Recorded sales"
            icon="🛒"
          />

          <StatCard
            title="Revenue"
            value={`₹${Number(
              summary?.total_revenue ?? 0
            ).toLocaleString()}`}
            subtitle="Recorded revenue"
            icon="💰"
          />
        </div>

        <div className="dashboard-grid">
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>📊 Risk Distribution</h2>

                <p>
                  Current AI risk across products
                </p>
              </div>
            </div>

            {analytics?.risk_distribution?.length ? (
              <div
                style={{
                  display: "grid",
                  gap: "12px",
                }}
              >
                {analytics.risk_distribution.map(
                  (item) => (
                    <div
                      key={item.risk_level}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent:
                          "space-between",
                        padding: "12px",
                        border: "1px solid #e5e7eb",
                        borderRadius: "10px",
                      }}
                    >
                      <RiskBadge
                        risk={item.risk_level}
                      />

                      <strong>
                        {item.count} products
                      </strong>
                    </div>
                  )
                )}
              </div>
            ) : (
              <EmptyState message="No risk distribution data available." />
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>📦 Category Distribution</h2>

                <p>
                  Products and inventory by category
                </p>
              </div>
            </div>

            {analytics?.category_distribution?.length ? (
              <div
                style={{
                  display: "grid",
                  gap: "10px",
                }}
              >
                {analytics.category_distribution.map(
                  (item) => (
                    <div
                      key={item.category}
                      style={{
                        display: "flex",
                        justifyContent:
                          "space-between",
                        padding: "12px",
                        borderBottom:
                          "1px solid #e5e7eb",
                      }}
                    >
                      <strong>
                        {item.category}
                      </strong>

                      <span>
                        {item.count} products ·{" "}
                        {item.total_stock} units
                      </span>
                    </div>
                  )
                )}
              </div>
            ) : (
              <EmptyState message="No category data available." />
            )}
          </section>
        </div>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>🚨 Urgent Products</h2>

              <p>
                Products requiring inventory attention
              </p>
            </div>
          </div>

          {analytics?.urgent_products?.length ? (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Category</th>
                    <th>Stock</th>
                    <th>Daily Sales</th>
                    <th>Stockout</th>
                    <th>Risk</th>
                    <th>Restock</th>
                  </tr>
                </thead>

                <tbody>
                  {analytics.urgent_products.map(
                    (product) => (
                      <tr key={product.id}>
                        <td>
                          <strong>
                            {product.name}
                          </strong>

                          <small>
                            {product.sku}
                          </small>
                        </td>

                        <td>{product.category}</td>

                        <td>
                          {product.current_stock}
                        </td>

                        <td>
                          {product.average_daily_sales !=
                          null
                            ? Number(
                                product.average_daily_sales
                              ).toFixed(1)
                            : "—"}
                        </td>

                        <td>
                          {product.predicted_stockout_days !=
                          null
                            ? `${Math.round(
                                product.predicted_stockout_days
                              )} days`
                            : "—"}
                        </td>

                        <td>
                          <RiskBadge
                            risk={product.risk_level}
                          />
                        </td>

                        <td>
                          {product.recommended_restock ??
                            0}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message="No urgent products detected." />
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>📈 Recent Sales Trend</h2>

              <p>
                Last 30 days of recorded sales
              </p>
            </div>
          </div>

          {analytics?.recent_sales_trend?.length ? (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Units Sold</th>
                    <th>Revenue</th>
                  </tr>
                </thead>

                <tbody>
                  {analytics.recent_sales_trend.map(
                    (item) => (
                      <tr key={item.date}>
                        <td>{item.date}</td>

                        <td>{item.sales_units}</td>

                        <td>
                          ₹
                          {Number(
                            item.revenue ?? 0
                          ).toLocaleString()}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message="No recent sales data available." />
          )}
        </section>
      </>
    );
  };

  /*
   * ---------------------------------------------------------
   * CURRENT PAGE
   * ---------------------------------------------------------
   */

  const renderCurrentPage = () => {
    if (activePage === "Dashboard") {
      return renderDashboard();
    }

    if (activePage === "Products") {
      return renderProducts();
    }

    if (activePage === "Predictions") {
      return renderPredictions();
    }

    if (activePage === "Alerts") {
      return renderAlerts();
    }

    if (activePage === "Analytics") {
      return renderAnalytics();
    }

    return renderDashboard();
  };

  /*
   * ---------------------------------------------------------
   * APP UI
   * ---------------------------------------------------------
   */

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">S</div>

          <div>
            <h2>StockSense</h2>
            <span>AI Inventory</span>
          </div>
        </div>

        <nav>
          {[
            "Dashboard",
            "Products",
            "Predictions",
            "Alerts",
            "Analytics",
          ].map((item) => (
            <button
              key={item}
              className={
                activePage === item ? "active" : ""
              }
              onClick={() =>
                handlePageChange(item)
              }
            >
              <span>
                {{
                  Dashboard: "▦",
                  Products: "📦",
                  Predictions: "🧠",
                  Alerts: "🔔",
                  Analytics: "📊",
                }[item]}
              </span>

              {item}

              {item === "Alerts" &&
                unreadAlerts.length > 0 && (
                  <span
                    style={{
                      marginLeft: "auto",
                      minWidth: "22px",
                      height: "22px",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "999px",
                      background: "#ef4444",
                      color: "#fff",
                      fontSize: "11px",
                      fontWeight: "700",
                    }}
                  >
                    {unreadAlerts.length}
                  </span>
                )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="ai-status">
            <div className="status-dot"></div>

            <div>
              <strong>AI Engine Online</strong>

              <span>
                Prediction system active
              </span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">
              StockSense AI
            </span>
          </div>

          <div className="topbar-right">
            {/* NOTIFICATION BUTTON */}
            <div
              className="notification"
              onClick={() =>
                setNotificationOpen(
                  !notificationOpen
                )
              }
              style={{
                cursor: "pointer",
                position: "relative",
              }}
              title="Notifications"
            >
              🔔

              {unreadAlerts.length > 0 && (
                <span>{unreadAlerts.length}</span>
              )}

              {notificationOpen && (
                <div
                  style={{
                    position: "absolute",
                    top: "42px",
                    right: "0",
                    width: "360px",
                    maxWidth:
                      "calc(100vw - 40px)",
                    background: "#ffffff",
                    border: "1px solid #e5e7eb",
                    borderRadius: "12px",
                    boxShadow:
                      "0 12px 30px rgba(0,0,0,0.15)",
                    padding: "14px",
                    zIndex: 100,
                    color: "#111827",
                  }}
                  onClick={(e) =>
                    e.stopPropagation()
                  }
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent:
                        "space-between",
                      alignItems: "center",
                      marginBottom: "10px",
                    }}
                  >
                    <strong>Notifications</strong>

                    {unreadAlerts.length > 0 && (
                      <button
                        className="small-btn"
                        onClick={
                          markAllAlertsRead
                        }
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  {alerts.length === 0 ? (
                    <p>No notifications.</p>
                  ) : (
                    <div
                      style={{
                        display: "grid",
                        gap: "8px",
                        maxHeight: "320px",
                        overflowY: "auto",
                      }}
                    >
                      {alerts.slice(0, 6).map(
                        (alert) => (
                          <div
                            key={alert.id}
                            style={{
                              padding: "10px",
                              borderRadius: "8px",
                              background:
                                alert.is_read
                                  ? "#f9fafb"
                                  : "#eff6ff",
                              border:
                                "1px solid #e5e7eb",
                            }}
                          >
                            <strong>
                              {alert.product_name}
                            </strong>

                            <p
                              style={{
                                margin: "4px 0",
                                fontSize: "13px",
                              }}
                            >
                              {alert.message}
                            </p>

                            {!alert.is_read && (
                              <button
                                className="read-btn"
                                onClick={() =>
                                  markAlertRead(
                                    alert.id
                                  )
                                }
                              >
                                Mark read
                              </button>
                            )}
                          </div>
                        )
                      )}
                    </div>
                  )}

                  <button
                    className="small-btn"
                    style={{
                      marginTop: "10px",
                      width: "100%",
                    }}
                    onClick={() =>
                      handlePageChange("Alerts")
                    }
                  >
                    View all alerts
                  </button>
                </div>
              )}
            </div>

            {/* VENDOR PROFILE */}
            <div
              className="user-profile"
              onClick={() => {
                setNotificationOpen(false);
                setProfileOpen(!profileOpen);
              }}
              style={{
                cursor: "pointer",
                position: "relative",
              }}
              title="Open Vendor Profile"
            >
              <div className="user-avatar">V</div>

              <div>
                <strong>Vendor</strong>

                <span>Inventory Manager</span>
              </div>

              {profileOpen && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    position: "absolute",
                    top: "50px",
                    right: "0",
                    width: "280px",
                    background: "#ffffff",
                    border: "1px solid #e5e7eb",
                    borderRadius: "12px",
                    boxShadow:
                      "0 12px 30px rgba(0,0,0,0.15)",
                    padding: "18px",
                    zIndex: 200,
                    color: "#111827",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      paddingBottom: "15px",
                      borderBottom:
                        "1px solid #e5e7eb",
                    }}
                  >
                    <div
                      style={{
                        width: "48px",
                        height: "48px",
                        borderRadius: "50%",
                        background: "#800000",
                        color: "#ffffff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "18px",
                        fontWeight: "700",
                      }}
                    >
                      V
                    </div>

                    <div>
                      <strong
                        style={{
                          display: "block",
                          fontSize: "16px",
                        }}
                      >
                        Vendor
                      </strong>

                      <span
                        style={{
                          display: "block",
                          marginTop: "4px",
                          fontSize: "12px",
                          color: "#6b7280",
                        }}
                      >
                        Inventory Manager
                      </span>
                    </div>
                  </div>

                  <div style={{ paddingTop: "15px" }}>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#6b7280",
                        textTransform: "uppercase",
                        marginBottom: "5px",
                      }}
                    >
                      Profile Name
                    </div>

                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: "600",
                      }}
                    >
                      Vendor
                    </div>
                  </div>

                  <div style={{ paddingTop: "13px" }}>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#6b7280",
                        textTransform: "uppercase",
                        marginBottom: "5px",
                      }}
                    >
                      Role
                    </div>

                    <div
                      style={{
                        fontSize: "14px",
                        fontWeight: "600",
                      }}
                    >
                      Inventory Manager
                    </div>
                  </div>

                  <div style={{ paddingTop: "13px" }}>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#6b7280",
                        textTransform: "uppercase",
                        marginBottom: "5px",
                      }}
                    >
                      Account
                    </div>

                    <div
                      style={{
                        fontSize: "14px",
                      }}
                    >
                      Vendor Account
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      api.setToken(null);
                      setProfileOpen(false);
                      window.location.reload();
                    }}
                    style={{
                      width: "100%",
                      marginTop: "18px",
                      padding: "10px 12px",
                      border: "none",
                      borderRadius: "8px",
                      background: "#800000",
                      color: "#ffffff",
                      cursor: "pointer",
                      fontWeight: "600",
                    }}
                  >
                    Logout
                  </button>

                  <button
                    onClick={() => setProfileOpen(false)}
                    style={{
                      width: "100%",
                      marginTop: "8px",
                      padding: "9px 12px",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                      background: "#f9fafb",
                      color: "#111827",
                      cursor: "pointer",
                      fontWeight: "600",
                    }}
                  >
                    Close
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="content">
          {renderCurrentPage()}
        </div>
      </main>
    </div>
  );
}

export default App;