<template>
  <div class="home-container">
    <nav class="navbar">
      <div class="nav-brand">SYNTHETICA</div>
      <div class="nav-links">
        <a href="https://github.com/saksham-jain177/synthetica-cognitive-sandbox" target="_blank" class="github-link">
          Github <span class="arrow">↗</span>
        </a>
      </div>
    </nav>
    <div class="main-content">
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag">OBSERVABILITY NODE</span>
            <span class="version-text">/ v1.0.0</span>
          </div>
          <h1 class="main-title">
            Project<br>
            <span class="gradient-text">Synthetica</span>
          </h1>
          <div class="hero-desc">
            <p>
              A 6GB VRAM-optimized Cognitive Sandbox investigating emergent rule-breaking and ideological evolution in adversarial Swarm Intelligence.
            </p>
            <p class="slogan-text">
               Run `python run_synthetica.py` on your backend to generate simulation records, then view the memory graphs below.<span class="blinking-cursor">_</span>
            </p>
          </div>
        </div>
      </section>
      <!-- Zep Graph Memory Database Visualizer -->
      <HistoryDatabase />
    </div>
  </div>
</template>

<script setup>
import HistoryDatabase from '../components/HistoryDatabase.vue'
</script>

<style scoped>
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --gray-light: #F5F5F5;
  --gray-text: #666666;
  --border: #E5E5E5;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
}
.home-container {
  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-sans);
  color: var(--black);
}
.navbar {
  height: 60px;
  background: var(--black);
  color: var(--white);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}
.nav-brand {
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
}
.nav-links {
  display: flex;
  align-items: center;
}
.github-link {
  color: var(--white);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
}
.hero-left {
  flex: 1;
  padding-right: 60px;
}
.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}
.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
}
.version-text {
  color: #999;
  font-weight: 500;
}
.main-title {
  font-size: 4.5rem;
  line-height: 1.2;
  font-weight: 500;
  margin: 0 0 40px 0;
  letter-spacing: -2px;
}
.gradient-text {
  background: linear-gradient(90deg, #000000 0%, #444444 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}
.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--gray-text);
  max-width: 640px;
  margin-bottom: 50px;
}
.slogan-text {
  font-size: 1.2rem;
  font-weight: 520;
  color: var(--black);
  border-left: 3px solid var(--orange);
  padding-left: 15px;
  margin-top: 20px;
}
.blinking-cursor {
  color: var(--orange);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
