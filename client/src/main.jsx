import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { installPartyUpgrade } from "./partyUpgrade.js";
import "./styles.css";
import "./partyUpgrade.css";

installPartyUpgrade();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
