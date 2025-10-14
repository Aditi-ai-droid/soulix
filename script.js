const canvas = document.getElementById("cloudCanvas");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener("resize", resizeCanvas);

// create particles (soft clouds)
const clouds = [];
for (let i = 0; i < 60; i++) {
  clouds.push({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height - canvas.height,
    size: 100 + Math.random() * 250,
    speed: 0.2 + Math.random() * 0.4,
    opacity: 0.05 + Math.random() * 0.1,
  });
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  clouds.forEach((c) => {
    const gradient = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, c.size);
    gradient.addColorStop(0, `rgba(255,255,255,${c.opacity})`);
    gradient.addColorStop(0.5, `rgba(220,240,230,${c.opacity * 0.7})`);
    gradient.addColorStop(1, "transparent");

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(c.x, c.y, c.size, 0, Math.PI * 2);
    ctx.fill();

    c.y += c.speed;
    c.x += Math.sin(c.y / 200) * 0.3;

    if (c.y > canvas.height + 200) {
      c.y = -200;
      c.x = Math.random() * canvas.width;
    }
  });
  requestAnimationFrame(draw);
}

draw();
