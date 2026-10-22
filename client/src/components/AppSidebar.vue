<template>
  <aside class="sidebar" :class="{ open }">
    <div class="sidebar-brand">
      <span class="brand-name">{{ brand }}</span>
      <span v-if="subtitle" class="brand-subtitle">{{ subtitle }}</span>
    </div>

    <nav class="sidebar-nav" :aria-label="navLabel">
      <router-link
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :aria-current="isActive(item.to) ? 'page' : undefined"
        :class="{ active: isActive(item.to) }"
        @click="$emit('close')"
      >
        <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in iconPaths[item.icon]" :key="d" :d="d" />
        </svg>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <slot name="footer" />
    </div>
  </aside>
  <div v-if="open" class="sidebar-backdrop" @click="$emit('close')"></div>
</template>

<script>
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const iconPaths = {
  overview: ['M3 3h6v6H3z', 'M11 3h6v4h-6z', 'M11 9h6v8h-6z', 'M3 11h6v6H3z'],
  inventory: ['M3 6.5L10 3l7 3.5v7L10 17l-7-3.5z', 'M3 6.5L10 10l7-3.5', 'M10 10v7'],
  orders: ['M5 3h10v14H5z', 'M8 7h4', 'M8 10h4', 'M8 13h2'],
  finance: ['M3 16h14', 'M5 16V10', 'M10 16V5', 'M15 16V8'],
  demand: ['M3 14l4-4 3 3 7-7', 'M13 6h4v4'],
  reports: ['M6 3h6l4 4v10H6z', 'M12 3v4h4', 'M8 11h6', 'M8 14h4']
}

export default {
  name: 'AppSidebar',
  props: {
    open: { type: Boolean, default: false },
    brand: { type: String, required: true },
    subtitle: { type: String, default: '' },
    navLabel: { type: String, default: 'Main' },
    // [{ to, label, icon }]
    items: { type: Array, required: true }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const route = useRoute()

    const isActive = (to) => (to === '/' ? route.path === '/' : route.path.startsWith(to))

    const onKeydown = (e) => {
      if (e.key === 'Escape' && props.open) emit('close')
    }
    onMounted(() => window.addEventListener('keydown', onKeydown))
    onUnmounted(() => window.removeEventListener('keydown', onKeydown))

    return { isActive, iconPaths }
  }
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--color-border);
  z-index: 100;
  overflow-y: auto;
  transition: transform 0.2s ease;
}

.sidebar-brand {
  padding: var(--space-5) var(--space-4) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.brand-name {
  color: var(--color-text);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.025em;
  overflow-wrap: anywhere;
}

.brand-subtitle {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.sidebar-nav {
  flex: 1 0 auto;
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--sidebar-text);
  font-size: var(--text-base);
  font-weight: 500;
  text-decoration: none;
  transition: background var(--transition), color var(--transition);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-label {
  min-width: 0;
  overflow-wrap: anywhere;
}

.nav-item:hover {
  background: var(--sidebar-item-hover);
  color: var(--color-text);
}

.nav-item.active {
  background: var(--sidebar-item-active);
  color: var(--sidebar-text-active);
}

.nav-item:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }
  .sidebar.open {
    transform: translateX(0);
    box-shadow: var(--shadow-lg);
  }
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.5);
    z-index: 90;
  }
}
</style>
