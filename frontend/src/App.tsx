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
            <div className="logo-icon" aria-hidden="true">WA</div>
            <span className="logo-text">WebAudit Pro</span>
            <span className="header-badge">Beta</span>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main>
        <div className="container">
          <section className="hero">
            <p className="hero-eyebrow">Website Audit Platform</p>
            <h1 className="hero-title">
              Audit any website.
              <span className="hero-title-accent"> Get comprehensive reports.</span>
            </h1>
            <p className="hero-sub">
              Run structured audits for performance, SEO, accessibility,
              security, and functionality from a single dashboard.
            </p>
          </section>

          <Home />
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          WebAudit Pro · Automated website audits · Performance · SEO · Accessibility · Security
        </div>
      </footer>
    </div>
  );
};

export default App;
