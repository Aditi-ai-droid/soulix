import React from "react";

function App() {
  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "#121212", color: "white" }}>
      {/* Sidebar */}
      <div style={{ width: "250px", backgroundColor: "#1f1f1f", padding: "20px" }}>
        <h2 style={{ color: "#ffa500" }}>Dashboard</h2>
        <p>Home</p>
        <p>Analytics</p>
        <p>Settings</p>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, padding: "20px" }}>
        <h1>Welcome Back!</h1>
        <div style={{ display: "flex", gap: "20px", marginBottom: "40px" }}>
          <div style={{ backgroundColor: "#222", padding: "20px", borderRadius: "8px", flex: 1 }}>
            <h3>Users</h3>
            <p style={{ color: "#ffa500", fontWeight: "bold" }}>1,025</p>
          </div>
          <div style={{ backgroundColor: "#222", padding: "20px", borderRadius: "8px", flex: 1 }}>
            <h3>Conversion</h3>
            <p style={{ color: "#ffa500", fontWeight: "bold" }}>19.8%</p>
          </div>
          <div style={{ backgroundColor: "#222", padding: "20px", borderRadius: "8px", flex: 1 }}>
            <h3>Active</h3>
            <p style={{ color: "#ffa500", fontWeight: "bold" }}>832</p>
          </div>
        </div>

        {/* Chart placeholder */}
        <div style={{ backgroundColor: "#222", borderRadius: "8px", height: "300px" }}>
          <h3 style={{ padding: "20px" }}>Charts will go here</h3>
        </div>
      </div>
    </div>
  );
}

export default App;
