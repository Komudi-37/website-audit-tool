import React from "react";
import Home from "./pages/Home";
import "./index.css";

const App: React.FC = () => {
  return (
    <div className="app-wrapper">
      {/* Header */}
      <header className="header">
        <div className="container">
          <div className="header-inner">
            <div className="logo-icon" aria-hidden="true">🛰️</div>
            <span className="logo-text">WebAudit Pro</span>
            <span className="header-badge">MVP · Phase 1</span>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main>
        <div className="container">
          <section className="hero">
            <div className="hero-eyebrow">
              <span>✦</span> AI-Powered Audit Engine
            </div>
            <h1>
              Audit Any Website<br />
              <span>Instantly & Free</span>
            </h1>
            <p className="hero-sub">
              Analyze performance, SEO, accessibility, security, and
              functionality — all in one place.
            </p>
          </section>

          <Home />
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          WebAudit Pro · Built with FastAPI + React + Vite · Open Source MVP
        </div>
      </footer>
    </div>
  );
};

export default App;
