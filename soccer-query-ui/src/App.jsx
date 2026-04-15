import { useState } from "react";
import "./index.css";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const examples = [
    "How many matches did Manchester City play in EPL 2021-22?",
    "Manchester City home wins in 2021-22",
    "How many goals did Manchester City score in EPL?",
    "Real Sociedad home wins in LaLiga 2022-23 2023-24",
  ];

  async function runQuery() {
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE}/product/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Request failed");
      }

      setResponse(data);
    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function confirmAndRun() {
    if (!response?.confirm_payload) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/product/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(response.confirm_payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Confirmation failed");
      }

      setResponse(data);
    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function resetAll() {
    setQuery("");
    setResponse(null);
    setError("");
  }

  return (
    <div className="page">
      <div className="container">
        <div className="left-panel">
          <div className="card">
            <h1>Soccer Query Agent</h1>
            <p className="subtext">
              Structured query interface with confirmation for inferred fields.
            </p>

            <label className="label">Query</label>
            <textarea
              className="textarea"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a soccer analytics question..."
            />

            <div className="button-row">
              <button className="primary-btn" onClick={runQuery} disabled={loading}>
                {loading ? "Running..." : "Run Query"}
              </button>
              <button className="secondary-btn" onClick={resetAll} disabled={loading}>
                Reset
              </button>
            </div>

            {error ? <div className="error-box">{error}</div> : null}
          </div>

          <div className="card">
            <h2>Example Queries</h2>
            <div className="examples">
              {examples.map((item) => (
                <button
                  key={item}
                  className="example-btn"
                  onClick={() => {
                    setQuery(item);
                    setError("");
                  }}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="right-panel">
          <div className="card">
            <div className="result-header">
              <h2>Result</h2>
              <span className={`badge badge-${response?.status || "idle"}`}>
                {response?.status || "idle"}
              </span>
            </div>

            {!response ? (
              <div className="placeholder">Run a query to see the result.</div>
            ) : response.status === "needs_confirmation" ? (
              <div className="confirmation-block">
                <div className="confirm-box">
                  <div className="confirm-title">{response.title}</div>
                  <div className="confirm-message">{response.message}</div>
                  <button className="confirm-btn" onClick={confirmAndRun} disabled={loading}>
                    {loading ? "Confirming..." : "Confirm and Run"}
                  </button>
                </div>

                <div className="info-grid">
                  <div className="mini-card">
                    <div className="mini-title">Inferred Fields</div>
                    <div className="mini-value">
                      {response.inferred_fields?.length
                        ? response.inferred_fields.join(", ")
                        : "None"}
                    </div>
                  </div>

                  <div className="mini-card">
                    <div className="mini-title">Proposed Interpretation</div>
                    <pre className="json-box">
                      {JSON.stringify(response.proposed_interpretation, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <div className="final-block">
                <div className="answer-card">
                  <div className="mini-title">Answer</div>
                  <div className="answer-value">
                    {response.answer !== null && response.answer !== undefined
                      ? response.answer
                      : "—"}
                  </div>
                </div>

                <div className="info-grid">
                  <div className="mini-card">
                    <div className="mini-title">Message</div>
                    <div className="mini-value">{response.message || "—"}</div>
                  </div>

                  <div className="mini-card">
                    <div className="mini-title">Query Type</div>
                    <div className="mini-value">{response.query_type || "—"}</div>
                  </div>

                  <div className="mini-card">
                    <div className="mini-title">Validator Decision</div>
                    <div className="mini-value">{response.validator_decision || "—"}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
