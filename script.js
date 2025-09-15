// Bar Chart
const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx, {
  type: 'bar',
  data: {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    datasets: [{
      label: 'Users',
      data: [120, 190, 300, 500, 200, 300],
      backgroundColor: '#f5b041'
    }]
  },
  options: {
    responsive: true,
    scales: {
      y: {
        ticks: { color: '#fff' },
        grid: { color: '#333' }
      },
      x: {
        ticks: { color: '#fff' },
        grid: { color: '#333' }
      }
    },
    plugins: {
      legend: {
        labels: { color: '#fff' }
      }
    }
  }
});

// Pie Chart
const pieCtx = document.getElementById('pieChart').getContext('2d');
new Chart(pieCtx, {
  type: 'doughnut',
  data: {
    labels: ['Active', 'Inactive'],
    datasets: [{
      label: 'User Status',
      data: [70, 30],
      backgroundColor: ['#f5b041', '#444']
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: {
        labels: { color: '#fff' }
      }
    }
  }
});
