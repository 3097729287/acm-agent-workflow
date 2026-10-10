import React from "react";
import { createRoot } from "react-dom/client";
import App from "@/app/App.jsx";
import "@/styles/workspace.css";
import "@/styles/refinements.css";
import "katex/dist/katex.min.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
