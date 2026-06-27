import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { PmsProvider } from "./context/PmsContext";
import "./styles/tokens.css";
import "./styles.css";
import "./styles/design-system.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <PmsProvider>
        <App />
      </PmsProvider>
    </BrowserRouter>
  </React.StrictMode>
);
