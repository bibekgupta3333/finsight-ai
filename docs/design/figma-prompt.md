# Figma Design Prompt - FinSight AI Frontend

## 📋 Project Overview

Create a modern, professional UI design for **FinSight AI** - a multimodal personal finance reasoning agent web application. The design should be clean, trustworthy, data-focused, and accessible.

---

## 🎨 Design System

### Color Palette

#### Primary Colors (Financial Trust)
- **Primary Blue:** `#2563EB` (Trust, professionalism)
  - Light: `#3B82F6`
  - Dark: `#1E40AF`
- **Secondary Green:** `#10B981` (Success, positive trends)
  - Light: `#34D399`
  - Dark: `#059669`

#### Semantic Colors
- **Success:** `#10B981` (Green)
- **Warning:** `#F59E0B` (Amber)
- **Danger:** `#EF4444` (Red)
- **Info:** `#3B82F6` (Blue)

#### Neutral Colors
- **Background Light:** `#FFFFFF`
- **Background Dark:** `#0F172A`
- **Surface:** `#F8FAFC`
- **Border:** `#E2E8F0`
- **Text Primary:** `#1E293B`
- **Text Secondary:** `#64748B`
- **Text Muted:** `#94A3B8`

#### Chart Colors (Data Visualization)
```
Categories (8 colors):
1. #3B82F6 - Food & Dining
2. #10B981 - Transportation
3. #8B5CF6 - Shopping
4. #F59E0B - Housing
5. #EF4444 - Entertainment
6. #EC4899 - Health
7. #06B6D4 - Subscriptions
8. #64748B - Other
```

### Typography

#### Font Families
```
Primary (Body): "Inter", system-ui, sans-serif
Headings: "Inter", system-ui, sans-serif
Monospace (Data): "JetBrains Mono", "Courier New", monospace
```

#### Font Scales
```
xs:   12px / 0.75rem   (labels, captions)
sm:   14px / 0.875rem  (body small)
base: 16px / 1rem      (body)
lg:   18px / 1.125rem  (large body)
xl:   20px / 1.25rem   (h4)
2xl:  24px / 1.5rem    (h3)
3xl:  30px / 1.875rem  (h2)
4xl:  36px / 2.25rem   (h1)
5xl:  48px / 3rem      (hero)
```

#### Font Weights
```
Regular: 400
Medium:  500
Semibold: 600
Bold:    700
```

### Spacing System
```
xs:  4px
sm:  8px
md:  16px
lg:  24px
xl:  32px
2xl: 48px
3xl: 64px
```

### Border Radius
```
sm: 4px   (buttons, inputs)
md: 8px   (cards)
lg: 12px  (modals)
xl: 16px  (feature cards)
full: 9999px (pills, avatars)
```

### Shadows
```
sm: 0 1px 2px 0 rgb(0 0 0 / 0.05)
md: 0 4px 6px -1px rgb(0 0 0 / 0.1)
lg: 0 10px 15px -3px rgb(0 0 0 / 0.1)
xl: 0 20px 25px -5px rgb(0 0 0 / 0.1)
```

---

## 📱 Screen Layouts

### 1. Landing Page / Hero Section

**Viewport:** Desktop (1440px), Tablet (768px), Mobile (375px)

**Elements:**
```
┌─────────────────────────────────────────────────────────┐
│ [Logo] FinSight AI     [Features] [Pricing] [Sign In]  │ ← Navigation Bar
├─────────────────────────────────────────────────────────┤
│                                                          │
│          🎯 Your AI-Powered Financial Advisor           │ ← Hero Headline (5xl, bold)
│                                                          │
│     Analyze bank statements, detect spending patterns,  │ ← Subheadline (lg)
│     and get intelligent financial insights - all with   │
│              multimodal AI reasoning.                    │
│                                                          │
│     [Upload Statement →]  [Watch Demo]                  │ ← CTAs
│                                                          │
│     ┌─────────────────────────────────────────┐        │
│     │   [Dashboard Screenshot/Preview]         │        │ ← Hero Image
│     │   (Gradient border, shadow xl)           │        │
│     └─────────────────────────────────────────┘        │
│                                                          │
├─────────────────────────────────────────────────────────┤
│              ✨ Key Features Section                     │
│                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│  │ 📄 Multi│    │ 🤖 Smart│    │ 📊 Visual│            │
│  │  modal  │    │  Agent  │    │ Insights │            │
│  └─────────┘    └─────────┘    └─────────┘            │
└─────────────────────────────────────────────────────────┘
```

**Key Elements:**
- Hero headline with gradient text effect
- Two-column layout (text left, visual right)
- Animated statistics counter (e.g., "10K+ transactions analyzed")
- Social proof section (testimonials/logos)
- Smooth scroll animations

---

### 2. Upload Page

**Layout:** Centered upload interface

```
┌─────────────────────────────────────────────────────────┐
│ [←] Upload Documents                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│     Step 1 of 3: Upload Your Documents                  │
│     ━━━━━━━━━━━━━━━━━━━━━━━━                         │ ← Progress bar
│                                                          │
│     ┌───────────────────────────────────────┐          │
│     │  ┌─────────────────────────────┐      │          │
│     │  │                             │      │          │
│     │  │     📁                      │      │          │
│     │  │                             │      │          │
│     │  │  Drag & drop files here     │      │          │ ← Drop zone
│     │  │  or click to browse         │      │          │   (dashed border)
│     │  │                             │      │          │
│     │  │  PDF, PNG, JPG (max 10MB)  │      │          │
│     │  └─────────────────────────────┘      │          │
│     └───────────────────────────────────────┘          │
│                                                          │
│     Recent Uploads:                                      │
│     ┌─────────────────────────────────────┐            │
│     │ 📄 bank_statement.pdf    [x]        │            │
│     │    2.3 MB • Uploaded 2 min ago      │            │
│     └─────────────────────────────────────┘            │
│                                                          │
│                    [Continue →]                          │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Drag-and-drop zone with hover state
- File preview thumbnails
- Upload progress indicators
- File type validation feedback
- Multi-file upload support

---

### 3. Dashboard Page

**Layout:** Sidebar + Main Content

```
┌──────────┬──────────────────────────────────────────────┐
│          │  Dashboard                    [🔔] [👤]      │
│  [Logo]  ├──────────────────────────────────────────────┤
│          │                                               │
│  📊 Dash │  Financial Health Score                      │
│  📁 Trans│  ┌─────────────────────────────────┐         │
│  📈 Insig│  │      ⭐ 78/100                  │         │
│  ⚙️ Setti│  │   [Circular progress chart]    │         │
│          │  └─────────────────────────────────┘         │
│          │                                               │
│          │  Spending This Month                         │
│          │  ┌─────────────────┬─────────────────┐       │
│          │  │  $2,847.50      │  [Line Chart]  │       │
│          │  │  ↑ 12% vs last │  7-day trend   │       │
│          │  └─────────────────┴─────────────────┘       │
│          │                                               │
│          │  Category Breakdown                          │
│          │  ┌─────────────────────────────────┐         │
│          │  │  [Donut Chart]  [Legend]       │         │
│          │  │                                  │         │
│          │  │  • Food: 35%    • Transport: 20%│         │
│          │  │  • Shopping: 18% • Other: 27%   │         │
│          │  └─────────────────────────────────┘         │
│          │                                               │
│          │  Recent Transactions                         │
│          │  ┌─────────────────────────────────┐         │
│          │  │ 🍔 Chipotle         -$12.50    │         │
│          │  │ Today, 12:30 PM                 │         │
│          │  ├─────────────────────────────────┤         │
│          │  │ ⛽ Shell Gas        -$45.00    │         │
│          │  │ Today, 8:15 AM                  │         │
│          │  └─────────────────────────────────┘         │
└──────────┴──────────────────────────────────────────────┘
```

**Sidebar Items:**
- Dashboard (active state with background)
- Transactions
- Insights
- Settings
- Help

**Cards:**
- Glass morphism effect (subtle)
- Hover elevation
- Loading skeleton states
- Empty states with illustrations

---

### 4. Insights Page

**Layout:** Feed-style insights cards

```
┌─────────────────────────────────────────────────────────┐
│  AI Insights                          [Filter ▼]         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ⚠️ Anomaly Detected                     [High Priority]│
│  ┌─────────────────────────────────────────┐           │
│  │  Unusual spending detected              │           │
│  │                                         │           │
│  │  Your restaurant spending increased by  │           │
│  │  45% this week ($327 vs avg $225).     │           │
│  │                                         │           │
│  │  🍔 Detected transactions:              │           │
│  │  • Chipotle (3x this week)             │           │
│  │  • Uber Eats (5x this week)            │           │
│  │                                         │           │
│  │  💡 Recommendation:                     │           │
│  │  Consider meal prepping to reduce costs│           │
│  │                                         │           │
│  │  [View Details]  [Dismiss]             │           │
│  └─────────────────────────────────────────┘           │
│                                                          │
│  💰 Savings Opportunity                  [Medium]       │
│  ┌─────────────────────────────────────────┐           │
│  │  You could save $45/month               │           │
│  │                                         │           │
│  │  We noticed 3 subscriptions you haven't │           │
│  │  used in 30 days:                       │           │
│  │  • Spotify Premium: $9.99/mo           │           │
│  │  • Netflix: $15.99/mo                  │           │
│  │  • Adobe CC: $19.99/mo                 │           │
│  │                                         │           │
│  │  [Review Subscriptions]                │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

**Insight Card Types:**
1. Anomaly Alert (Red accent)
2. Savings Opportunity (Green accent)
3. Trend Analysis (Blue accent)
4. Budget Warning (Amber accent)

---

### 5. Transaction Details Modal

```
┌─────────────────────────────────────────────────────────┐
│  Transaction Details                           [✕]      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🍔 Chipotle Mexican Grill                              │
│  $12.50                                                  │
│  December 26, 2025 • 12:30 PM                           │
│                                                          │
│  ─────────────────────────────────────────              │
│                                                          │
│  Category:     [Food & Dining ▼]                        │
│  Payment:      Visa •••• 4242                           │
│  Status:       ✓ Completed                              │
│  Confidence:   95%                                       │
│                                                          │
│  🤖 AI Analysis:                                         │
│  ┌──────────────────────────────────────┐              │
│  │ This is your 3rd visit to Chipotle  │              │
│  │ this week, which is above your usual │              │
│  │ average of 1x per week.              │              │
│  └──────────────────────────────────────┘              │
│                                                          │
│  Notes:                                                  │
│  [Add a note...]                                        │
│                                                          │
│  [Save Changes]  [Delete Transaction]                   │
└─────────────────────────────────────────────────────────┘
```

---

### 6. Settings Page

**Layout:** Tabs + Forms

```
┌─────────────────────────────────────────────────────────┐
│  Settings                                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Profile] [Preferences] [Security] [Billing]           │
│  ━━━━━━━                                                │ ← Active tab
│                                                          │
│  Profile Information                                     │
│  ┌──────────────────────────────────────┐              │
│  │  Full Name                           │              │
│  │  [John Doe                          ]│              │
│  │                                      │              │
│  │  Email                               │              │
│  │  [john@example.com                  ]│              │
│  │                                      │              │
│  │  Profile Picture                     │              │
│  │  [👤 Upload new picture]            │              │
│  └──────────────────────────────────────┘              │
│                                                          │
│  Danger Zone                                             │
│  ┌──────────────────────────────────────┐              │
│  │  Delete Account                      │              │
│  │  Permanently delete your account     │              │
│  │  [Delete Account]                    │              │
│  └──────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 🎭 Component Library

### Buttons

```
Primary:
[Primary Button]
- Background: Primary Blue
- Text: White
- Hover: Darken 10%
- Active: Darken 15%

Secondary:
[Secondary Button]
- Background: Transparent
- Border: 1px Primary Blue
- Text: Primary Blue
- Hover: Light Blue Background

Danger:
[Delete]
- Background: Red
- Text: White

Ghost:
[Cancel]
- Background: Transparent
- Text: Text Secondary
- Hover: Surface
```

### Input Fields

```
Default:
┌──────────────────────────┐
│ Label                    │
│ [Placeholder text      ] │
│ Helper text              │
└──────────────────────────┘

Error State:
┌──────────────────────────┐
│ Email                    │
│ [john@                 ] │ ← Red border
│ ❌ Invalid email format  │
└──────────────────────────┘
```

### Cards

```
┌─────────────────────────────┐
│  Card Title        [•••]    │ ← Header
├─────────────────────────────┤
│  Card content goes here     │ ← Body
│                             │
│  Additional information     │
├─────────────────────────────┤
│  [Action 1]  [Action 2]    │ ← Footer (optional)
└─────────────────────────────┘

Variants:
- Default: White background
- Elevated: Shadow md
- Outlined: Border only
- Interactive: Hover effect
```

### Charts

**Line Chart:**
- Smooth curves
- Gradient fill (optional)
- Grid lines (subtle)
- Tooltips on hover
- Legend

**Donut Chart:**
- Category colors
- Center text (total amount)
- Interactive segments
- Percentage labels

**Bar Chart:**
- Horizontal or vertical
- Rounded corners
- Hover effects
- Comparison mode

---

## 🔄 Interactions & Animations

### Page Transitions
```
Duration: 200-300ms
Easing: ease-in-out
Effect: Fade + slight slide
```

### Button Hover
```
Transform: scale(1.02)
Duration: 150ms
Shadow: Increase
```

### Card Hover
```
Transform: translateY(-2px)
Shadow: Elevation increase
Duration: 200ms
```

### Loading States
```
Skeleton screens (not spinners)
Shimmer effect
Pulse animation
```

### Toast Notifications
```
Position: Top-right
Animation: Slide in from right
Auto-dismiss: 4 seconds
Close button: Yes
```

---

## 📐 Responsive Breakpoints

```
Mobile:    0px - 639px    (single column)
Tablet:    640px - 1023px (2 columns)
Desktop:   1024px - 1279px (full layout)
Large:     1280px+        (wide layout)
```

### Mobile Adaptations
- Hamburger menu
- Bottom navigation
- Full-width cards
- Stacked charts
- Collapsible sections

---

## ♿ Accessibility

### Color Contrast
- AA compliance minimum
- AAA for body text
- Test with contrast checker

### Focus States
- Visible focus ring (2px offset)
- Color: Primary Blue
- Never remove outline

### Keyboard Navigation
- Tab order logical
- Skip to content link
- Escape closes modals

### Screen Readers
- Semantic HTML
- ARIA labels
- Alt text for images
- Descriptive button text

---

## 🎨 Design Deliverables Checklist

### Required Screens (Desktop)
- [ ] Landing/Hero page
- [ ] Upload page (empty + with files)
- [ ] Dashboard (with data)
- [ ] Dashboard (loading state)
- [ ] Transactions list
- [ ] Transaction detail modal
- [ ] Insights feed
- [ ] Settings (all tabs)
- [ ] 404 Error page

### Required Screens (Mobile)
- [ ] Landing page (mobile)
- [ ] Dashboard (mobile)
- [ ] Bottom navigation
- [ ] Mobile menu

### Components
- [ ] Button variants
- [ ] Input fields (all states)
- [ ] Cards (all variants)
- [ ] Charts (line, donut, bar)
- [ ] Modals
- [ ] Toast notifications
- [ ] Loading skeletons
- [ ] Empty states
- [ ] Error states

### Assets
- [ ] Logo (SVG)
- [ ] Icons (consistent set)
- [ ] Illustrations (empty states)
- [ ] Favicons (all sizes)

---

## 🎯 Design Goals

1. **Trust:** Professional, clean, secure feeling
2. **Clarity:** Easy to understand financial data
3. **Efficiency:** Quick access to key information
4. **Delight:** Subtle animations, polished interactions
5. **Accessibility:** WCAG 2.1 AA compliant

---

## 📝 Figma-Specific Instructions

### Organization
```
Pages:
├── 🎨 Design System
│   ├── Colors
│   ├── Typography
│   ├── Components
│   └── Icons
├── 🖥️ Desktop Screens
│   ├── Landing
│   ├── Dashboard
│   ├── Transactions
│   └── Settings
├── 📱 Mobile Screens
└── 🔄 Flows
    ├── Upload Flow
    └── Analysis Flow
```

### Components to Create
- Button
- Input
- Card
- Modal
- Chart
- Navigation
- Sidebar
- Toast

### Variants
- Light/Dark mode
- Mobile/Desktop
- States (default, hover, active, disabled)

### Auto Layout
- Use for responsive components
- Set constraints properly
- Min/max widths defined

### Plugins Recommended
- Iconify (icons)
- Unsplash (images)
- Content Reel (dummy data)
- Contrast (accessibility)

---

**Good luck with the design! 🎨✨**
