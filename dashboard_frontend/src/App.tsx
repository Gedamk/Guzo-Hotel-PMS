import React from "react";
import "./App.css";
import { MonthlyPortfolioDashboard } from "./components/MonthlyPortfolioDashboard";

function App() {
  return (
    <div className="App">
      <MonthlyPortfolioDashboard year={2025} month={11} />
    </div>
  );
}

export default App;
