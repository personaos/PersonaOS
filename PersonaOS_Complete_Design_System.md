# PersonaOS Complete Design System
*A privacy-first, local-first AI assistant interface design system*

## Table of Contents
1. [Design Philosophy](#design-philosophy)
2. [Typography System](#typography-system)
3. [Color Palette](#color-palette)
4. [Spacing & Layout System](#spacing--layout-system)
5. [UI Components](#ui-components)
6. [Hero Landing Page](#hero-landing-page)
7. [Accessibility Guidelines](#accessibility-guidelines)
8. [Implementation Guidelines](#implementation-guidelines)

---

## Design Philosophy

PersonaOS embodies **future-tech minimalism** with a focus on:
- **Privacy-first**: Clean, trustworthy interface design
- **Local-first**: Professional, reliable aesthetic
- **Accessibility**: WCAG AA compliant with excellent contrast
- **Modularity**: Component-based system for scalability
- **No gradients**: Flat, solid colors for clean appearance
- **Dark-first**: Optimized for dark mode with light mode support

---

## Typography System

### Font Stack
```css
/* Primary Typography */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Monaco', 'Cascadia Code', monospace;

/* Font Weights */
--font-light: 300;
--font-regular: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-extrabold: 800;
```

### Typography Scale
```css
/* Font Sizes */
--text-xs: 0.75rem;    /* 12px - Tiny labels, captions */
--text-sm: 0.875rem;   /* 14px - Small text, metadata */
--text-base: 1rem;     /* 16px - Body text */
--text-lg: 1.125rem;   /* 18px - Large body text */
--text-xl: 1.25rem;    /* 20px - Card titles, small headings */
--text-2xl: 1.5rem;    /* 24px - Section headings */
--text-3xl: 1.875rem;  /* 30px - Page headings */
--text-4xl: 2.25rem;   /* 36px - Hero headings */
--text-5xl: 3rem;      /* 48px - Large hero text */
--text-6xl: 3.75rem;   /* 60px - Display headings */

/* Line Heights */
--leading-none: 1;
--leading-tight: 1.25;
--leading-snug: 1.375;
--leading-normal: 1.5;
--leading-relaxed: 1.625;
--leading-loose: 2;
```

### Heading Hierarchy
```css
h1 { font-size: var(--text-4xl); font-weight: var(--font-bold); line-height: var(--leading-tight); }
h2 { font-size: var(--text-3xl); font-weight: var(--font-semibold); line-height: var(--leading-tight); }
h3 { font-size: var(--text-2xl); font-weight: var(--font-semibold); line-height: var(--leading-snug); }
h4 { font-size: var(--text-xl); font-weight: var(--font-medium); line-height: var(--leading-snug); }
h5 { font-size: var(--text-lg); font-weight: var(--font-medium); line-height: var(--leading-normal); }
h6 { font-size: var(--text-base); font-weight: var(--font-semibold); line-height: var(--leading-normal); }

/* Body Text */
.body-large { font-size: var(--text-lg); line-height: var(--leading-relaxed); }
.body-base { font-size: var(--text-base); line-height: var(--leading-normal); }
.body-small { font-size: var(--text-sm); line-height: var(--leading-normal); }

/* Utility Classes */
.caption { font-size: var(--text-xs); color: var(--text-muted); }
.overline { font-size: var(--text-xs); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.1em; }
```

---

## Color Palette

### Core Brand Colors
```css
/* Primary Blue Spectrum */
--blue-50: #eff6ff;
--blue-100: #dbeafe;
--blue-200: #bfdbfe;
--blue-300: #93c5fd;
--blue-400: #60a5fa;
--blue-500: #3b82f6;    /* Primary Blue */
--blue-600: #2563eb;
--blue-700: #1d4ed8;
--blue-800: #1e40af;
--blue-900: #1e3a8a;

/* Secondary Purple Spectrum */
--purple-50: #faf5ff;
--purple-100: #f3e8ff;
--purple-200: #e9d5ff;
--purple-300: #d8b4fe;
--purple-400: #c084fc;
--purple-500: #a855f7;   /* Secondary Purple */
--purple-600: #9333ea;
--purple-700: #7c3aed;
--purple-800: #6b21a8;
--purple-900: #581c87;
```

### Dark Mode Color System
```css
:root {
  /* Backgrounds */
  --bg-primary: #0a0a0f;      /* Deep navy, almost black */
  --bg-secondary: #151520;    /* Card backgrounds */
  --bg-tertiary: #1f1f2e;     /* Elevated surfaces */
  --bg-elevated: #252540;     /* Modals, dropdowns */
  --bg-hover: #2a2a42;        /* Hover states */
  --bg-active: #303050;       /* Active/pressed states */

  /* Text Colors */
  --text-primary: #f8fafc;    /* High contrast white */
  --text-secondary: #cbd5e1;  /* Medium contrast */
  --text-tertiary: #94a3b8;   /* Lower contrast */
  --text-muted: #64748b;      /* Subtle text */
  --text-disabled: #475569;   /* Disabled states */

  /* Border Colors */
  --border-primary: #334155;  /* Default borders */
  --border-secondary: #475569; /* Subtle borders */
  --border-focus: var(--blue-500); /* Focus states */
  --border-hover: #64748b;    /* Hover borders */

  /* Brand Colors */
  --primary: var(--blue-500);
  --primary-hover: var(--blue-600);
  --primary-active: var(--blue-700);
  --secondary: var(--purple-500);
  --secondary-hover: var(--purple-600);
  --secondary-active: var(--purple-700);

  /* Semantic Colors */
  --success: #10b981;
  --success-bg: #064e3b;
  --warning: #f59e0b;
  --warning-bg: #78350f;
  --error: #ef4444;
  --error-bg: #7f1d1d;
  --info: var(--blue-500);
  --info-bg: #1e3a8a;
}
```

### Light Mode Color System
```css
[data-theme="light"] {
  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f1f5f9;
  --bg-elevated: #ffffff;
  --bg-hover: #f1f5f9;
  --bg-active: #e2e8f0;

  /* Text Colors */
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-tertiary: #64748b;
  --text-muted: #94a3b8;
  --text-disabled: #cbd5e1;

  /* Border Colors */
  --border-primary: #e2e8f0;
  --border-secondary: #cbd5e1;
  --border-hover: #94a3b8;

  /* Semantic Background Adjustments */
  --success-bg: #dcfce7;
  --warning-bg: #fef3c7;
  --error-bg: #fee2e2;
  --info-bg: #dbeafe;
}
```

### Usage Guidelines
- **Primary Blue**: CTAs, links, focus states, primary actions
- **Secondary Purple**: Secondary actions, accents, highlights
- **Backgrounds**: Layer from primary → secondary → tertiary for depth
- **Text**: Use hierarchy (primary → secondary → tertiary → muted)
- **Borders**: Subtle definition without overwhelming content

---

## Spacing & Layout System

### Spacing Scale
```css
--space-0: 0;
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-7: 1.75rem;   /* 28px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
--space-24: 6rem;     /* 96px */
--space-32: 8rem;     /* 128px */
```

### Container Sizes
```css
--container-xs: 480px;
--container-sm: 640px;
--container-md: 768px;
--container-lg: 1024px;
--container-xl: 1280px;
--container-2xl: 1536px;
--container-full: 100%;
```

### Grid System
```css
.grid {
  display: grid;
  gap: var(--space-6);
}

.grid-cols-1 { grid-template-columns: repeat(1, 1fr); }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid-cols-4 { grid-template-columns: repeat(4, 1fr); }
.grid-cols-12 { grid-template-columns: repeat(12, 1fr); }

/* Responsive Grid */
.grid-responsive {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-6);
}
```

---

## UI Components

### Buttons

#### Primary Button
```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: 0.5rem;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  line-height: 1;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  text-decoration: none;
  user-select: none;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.btn-primary:active {
  background: var(--primary-active);
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.btn-primary:disabled {
  background: var(--text-disabled);
  color: var(--text-muted);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
```

#### Secondary Button
```css
.btn-secondary {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.btn-secondary:active {
  background: var(--bg-active);
}

.btn-secondary:disabled {
  background: transparent;
  color: var(--text-disabled);
  border-color: var(--border-secondary);
  cursor: not-allowed;
}
```

#### Button Sizes
```css
.btn-sm {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
}

.btn-lg {
  padding: var(--space-4) var(--space-8);
  font-size: var(--text-lg);
}

.btn-icon {
  padding: var(--space-3);
  aspect-ratio: 1;
}
```

### Form Elements

#### Input Fields
```css
.input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  transition: all 0.2s ease;
}

.input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: var(--bg-primary);
}

.input::placeholder {
  color: var(--text-muted);
}

.input:disabled {
  background: var(--bg-primary);
  color: var(--text-disabled);
  cursor: not-allowed;
}

.input-error {
  border-color: var(--error);
}

.input-error:focus {
  border-color: var(--error);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}
```

#### Textarea
```css
.textarea {
  resize: vertical;
  min-height: 120px;
  font-family: inherit;
}
```

#### Checkbox & Radio
```css
.checkbox, .radio {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  user-select: none;
}

.checkbox input, .radio input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-box, .radio-box {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-primary);
  background: var(--bg-secondary);
  transition: all 0.2s ease;
  position: relative;
}

.checkbox-box {
  border-radius: 4px;
}

.radio-box {
  border-radius: 50%;
}

.checkbox:hover .checkbox-box,
.radio:hover .radio-box {
  border-color: var(--border-hover);
}

.checkbox input:checked + .checkbox-box,
.radio input:checked + .radio-box {
  background: var(--primary);
  border-color: var(--primary);
}

.checkbox input:checked + .checkbox-box::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 6px;
  width: 6px;
  height: 10px;
  border: 2px solid white;
  border-top: none;
  border-left: none;
  transform: rotate(45deg);
}

.radio input:checked + .radio-box::after {
  content: '';
  position: absolute;
  top: 4px;
  left: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
}
```

#### Toggle Switch
```css
.toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  user-select: none;
}

.toggle input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  width: 48px;
  height: 24px;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-primary);
  border-radius: 12px;
  position: relative;
  transition: all 0.3s ease;
}

.toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: all 0.3s ease;
}

.toggle input:checked + .toggle-slider {
  background: var(--primary);
  border-color: var(--primary);
}

.toggle input:checked + .toggle-slider::after {
  transform: translateX(24px);
  background: white;
}
```

### Dropdown Menus
```css
.dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-trigger {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
}

.dropdown-trigger:hover {
  border-color: var(--border-hover);
}

.dropdown-content {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  z-index: 100;
  margin-top: var(--space-1);
  overflow: hidden;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-8px);
  transition: all 0.2s ease;
}

.dropdown.open .dropdown-content {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.dropdown-item {
  padding: var(--space-3) var(--space-4);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  border-bottom: 1px solid var(--border-primary);
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.dropdown-item.selected {
  background: var(--primary);
  color: white;
}
```

### Tables
```css
.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-secondary);
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.table th {
  background: var(--bg-tertiary);
  padding: var(--space-4) var(--space-6);
  text-align: left;
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-primary);
}

.table td {
  padding: var(--space-4) var(--space-6);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.table tbody tr:hover {
  background: var(--bg-hover);
}

.table tbody tr:last-child td {
  border-bottom: none;
}

/* Alternating rows */
.table-striped tbody tr:nth-child(even) {
  background: var(--bg-primary);
}

.table-striped tbody tr:nth-child(even):hover {
  background: var(--bg-hover);
}
```

### Cards
```css
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
  transition: all 0.3s ease;
}

.card:hover {
  border-color: var(--border-hover);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.card-header {
  padding: var(--space-6);
  border-bottom: 1px solid var(--border-primary);
}

.card-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.card-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.card-body {
  padding: var(--space-6);
}

.card-footer {
  padding: var(--space-6);
  border-top: 1px solid var(--border-primary);
  background: var(--bg-primary);
}

/* Card Variants */
.card-interactive {
  cursor: pointer;
}

.card-interactive:hover {
  border-color: var(--primary);
}

.card-elevated {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
```

### Modals
```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
}

.modal-overlay.open {
  opacity: 1;
  visibility: visible;
}

.modal {
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 1rem;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow: hidden;
  transform: scale(0.95) translateY(20px);
  transition: all 0.3s ease;
}

.modal-overlay.open .modal {
  transform: scale(1) translateY(0);
}

.modal-header {
  padding: var(--space-6);
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: 0.25rem;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-6);
  color: var(--text-secondary);
}

.modal-footer {
  padding: var(--space-6);
  border-top: 1px solid var(--border-primary);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}
```

---

## Hero Landing Page

### Hero Section Layout
```css
.hero {
  min-height: 100vh;
  display: flex;
  align-items: center;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

.hero-container {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-16);
  align-items: center;
}

.hero-content {
  animation: fadeInUp 0.8s ease-out;
}

.hero-title {
  font-size: var(--text-6xl);
  font-weight: var(--font-extrabold);
  line-height: var(--leading-tight);
  color: var(--text-primary);
  margin-bottom: var(--space-6);
  background: linear-gradient(135deg, var(--text-primary) 0%, var(--primary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: var(--text-xl);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-8);
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.hero-cta {
  display: flex;
  gap: var(--space-4);
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.hero-visual {
  position: relative;
  animation: fadeInRight 0.8s ease-out 0.3s both;
}

.hero-placeholder {
  width: 100%;
  height: 400px;
  background: var(--bg-secondary);
  border: 2px dashed var(--border-primary);
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: var(--text-lg);
  position: relative;
  overflow: hidden;
}

.hero-placeholder::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: conic-gradient(from 0deg, transparent, var(--primary), transparent);
  animation: rotate 4s linear infinite;
  opacity: 0.1;
}

/* Animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .hero-container {
    grid-template-columns: 1fr;
    gap: var(--space-12);
    text-align: center;
  }
  
  .hero-title {
    font-size: var(--text-4xl);
  }
}
```

### Feature Cards Section
```css
.features {
  padding: var(--space-24) var(--space-6);
  background: var(--bg-secondary);
}

.features-container {
  max-width: var(--container-xl);
  margin: 0 auto;
}

.features-header {
  text-align: center;
  margin-bottom: var(--space-16);
}

.features-title {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-4);
}

.features-subtitle {
  font-size: var(--text-xl);
  color: var(--text-secondary);
  max-width: 600px;
  margin: 0 auto;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-8);
}

.feature-card {
  padding: var(--space-8);
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 1rem;
  text-align: center;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  border-color: var(--primary);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
}

.feature-icon {
  width: 64px;
  height: 64px;
  background: var(--primary);
  border-radius: 1rem;
  margin: 0 auto var(--space-6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: var(--text-2xl);
}

.feature-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}

.feature-description {
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}
```

---

## Accessibility Guidelines

### Color Contrast Compliance
- **Primary text on background**: 7.2:1 (AAA)
- **Secondary text on background**: 5.1:1 (AA+)
- **Tertiary text on background**: 4.6:1 (AA)
- **Interactive elements**: 4.5:1 minimum
- **Focus indicators**: 3:1 minimum

### Focus Management
```css
/* Focus Visible Polyfill */
.focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
  border-radius: 0.25rem;
}

/* Remove default focus for mouse users */
:focus:not(.focus-visible) {
  outline: none;
}

/* Enhanced focus for interactive elements */
.btn:focus-visible,
.input:focus-visible,
.dropdown-trigger:focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}
```

### Screen Reader Support
```css
/* Visually hidden but available to screen readers */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Skip to content link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 6px;
  background: var(--primary);
  color: white;
  padding: 8px;
  text-decoration: none;
  border-radius: 4px;
  z-index: 9999;
}

.skip-link:focus {
  top: 6px;
}
```

### Motion Preferences
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## Implementation Guidelines

### CSS Architecture
```css
/* Layer order for cascade management */
@layer reset, base, components, utilities;

/* CSS Custom Properties Organization */
:root {
  /* 1. Colors */
  /* 2. Typography */
  /* 3. Spacing */
  /* 4. Shadows */
  /* 5. Transitions */
}
```

### Theme Switching
```javascript
// Theme management utility
class ThemeManager {
  constructor() {
    this.theme = localStorage.getItem('theme') || 'dark';
    this.apply();
  }

  toggle() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    this.apply();
    localStorage.setItem('theme', this.theme);
  }

  apply() {
    document.documentElement.setAttribute('data-theme', this.theme);
  }
}

// Initialize theme
const themeManager = new ThemeManager();

// System preference detection
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches && !localStorage.getItem('theme')) {
  themeManager.theme = 'light';
  themeManager.apply();
}
```

### Component Usage Guidelines

#### Do's
- Use semantic HTML elements as the foundation
- Implement proper ARIA attributes for accessibility
- Follow the established color hierarchy
- Use consistent spacing from the scale
- Test with keyboard navigation
- Validate color contrast ratios
- Include hover and focus states for all interactive elements

#### Don'ts
- Don't use colors outside the defined palette
- Avoid fixed pixel values; use CSS custom properties
- Don't forget to test in both themes
- Avoid animations longer than 300ms
- Don't use insufficient color contrast
- Avoid gradients (per design requirements)

### Performance Considerations
- Use CSS custom properties for dynamic theming
- Implement efficient CSS selectors
- Minimize repaints with `transform` and `opacity` for animations
- Use `will-change` sparingly for complex animations
- Leverage CSS containment for large lists/tables

This comprehensive design system provides a solid foundation for building the PersonaOS interface with consistency, accessibility, and modern aesthetics while maintaining the privacy-first, local-first principles of the project.