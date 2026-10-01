// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
