import React from "react";
import { createRoot } from "react-dom/client";
import App from "./AppV2.jsx";
import "./workspace.css";
import "katex/dist/katex.min.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
