// Show last updated time
document.getElementById('last-updated').textContent =
  'Last updated: ' + new Date().toLocaleTimeString();

// Auto-refresh every 30 seconds
setTimeout(() => location.reload(), 30000);

// Restart buttons
document.querySelectorAll('.btn-restart').forEach(btn => {
  btn.addEventListener('click', async () => {
    const container = btn.dataset.container;
    btn.textContent = '↺ Restarting…';
    btn.disabled = true;
    try {
      const res  = await fetch(`/restart/${container}`, { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        btn.textContent = '✓ Done';
        setTimeout(() => location.reload(), 2000);
      } else {
        btn.textContent = '✗ Failed';
        btn.disabled = false;
      }
    } catch {
      btn.textContent = '✗ Error';
      btn.disabled = false;
    }
  });
});
