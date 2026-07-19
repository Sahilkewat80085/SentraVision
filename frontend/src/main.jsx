import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

// Locate root DOM element inside index.html
const rootElement = document.getElementById("root");

if (!rootElement) {
  console.error("Failed to find target root element '#root' in DOM tree.");
} else {
  // Initialize and mount React application inside StrictMode
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

