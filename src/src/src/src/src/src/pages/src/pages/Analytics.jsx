// src/pages/Analytics.jsx
import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from "recharts";

const dataBar = [
  { name: "Mon", users: 100 },
  { name: "Tue", users: 200 },
  { name: "Wed", users: 300 },
  { name: "Thu", users: 250 },
  { name: "Fri", users: 400 },
];

const dataPie = [
  { name: "Active", value: 832, color: "#ffa500" },
  { name: "Inactive", value: 268, color: "#444" },
];

export default function Analytics() {
  return (
    <div className="page">
      <h1>Analytics</h1>
      <div className="charts">
        <div className="chart neumorphism">
          <BarChart width={300} height={250} data={dataBar}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="users" fill="#ffa500" />
          </BarChart>
        </div>

        <div className="chart neumorphism">
          <PieChart width={300} height={250}>
            <Pie
              data={dataPie}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={80}
              label
            >
              {dataPie.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </div>
      </div>
    </div>
  );
}
