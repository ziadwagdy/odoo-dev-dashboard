<template>
  <div class="flex items-center gap-3">
    <!-- Icon -->
    <div class="relative">
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="40" height="40" rx="8" fill="url(#logoGradient)"/>
        <circle cx="20" cy="20" r="10" stroke="#E8B4D8" stroke-width="2" opacity="0.4"/>
        <circle cx="20" cy="20" r="5" fill="#C95FB5"/>
        <path d="M20 12v4M20 24v4M12 20h4M24 20h4" stroke="#E8B4D8" stroke-width="1.5" stroke-linecap="round"/>
        <defs>
          <linearGradient id="logoGradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#714B67"/>
            <stop offset="100%" stop-color="#A24689"/>
          </linearGradient>
        </defs>
      </svg>
      <!-- Animated pulse ring -->
      <div class="absolute inset-0 rounded-lg animate-ping opacity-20 bg-accent"></div>
    </div>
    
    <!-- Text -->
    <div class="flex flex-col">
      <h1 class="text-xl font-bold leading-none">
        <span class="bg-gradient-to-r from-white via-accent-light to-white bg-clip-text text-transparent">
          Odoo Dev
        </span>
      </h1>
      <span class="text-xs text-slate-400 font-medium tracking-wider uppercase">Dashboard</span>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
@keyframes ping {
  75%, 100% {
    transform: scale(1.1);
    opacity: 0;
  }
}

.animate-ping {
  animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}
</style>
