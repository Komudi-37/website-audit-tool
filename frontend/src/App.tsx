import React, { useEffect, useState } from "react";
import Home from "./pages/Home";
import "./index.css";

const App: React.FC = () => {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem("theme") as "dark" | "light") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === "dark" ? "light" : "dark");
  };

  return (
    <div className="app-wrapper">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>

      <header className="header">
        <div className="container">
          <div className="header-inner">
            <div className="logo-icon" aria-hidden="true">WA</div>
            <span className="logo-text">WebAudit Pro</span>
            <span className="header-badge">Beta</span>
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
          </div>
        </div>
      </header>

      <main id="main-content" tabIndex={-1}>
        <div className="container">
          <section className="hero" aria-labelledby="hero-title">
            <p className="hero-eyebrow">Website Audit Platform</p>
            <h1 id="hero-title" className="hero-title">
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

      <footer className="footer">
        <div className="container">
          WebAudit Pro · Automated website audits · Performance · SEO · Accessibility · Security
        </div>
      </footer>
    </div>
  );
};

export default App;