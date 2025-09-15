// src/components/Sidebar.jsx
import React from "react";
import { NavLink } from "react-router-dom";
import "./Sidebar.css"; // Optional for custom CSS

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <h2 className="logo">⚡ Soulix</h2>
      <nav>
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
    </aside>
  );
}
