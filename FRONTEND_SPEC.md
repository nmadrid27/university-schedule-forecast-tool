# Frontend Specification: Hybrid Streamlit + shadcn/ui Design System

**Project:** SCAD FOUN Enrollment Forecasting Tool
**Approach:** Hybrid - Streamlit Backend + shadcn-Inspired Frontend
**Timeline:** Quick (3-5 days)
**Target:** Production (Internal Department Use)
**Version:** 2.1.0

---

## Executive Summary

Redesign the chat interface using shadcn/ui's design principles while maintaining Streamlit's Python backend. This hybrid approach combines:
- **Streamlit** for Python logic, data processing, and deployment
- **shadcn/ui design tokens** for modern, accessible UI
- **Custom HTML/CSS/JS** injected via Streamlit's `st.markdown()` and `st.components.v1`
- **Tailwind CSS (CDN)** for utility-first styling
- **Zero build step** - everything works via CDN and inline code

---

## 1. Architecture Overview

### Current Architecture
```
┌─────────────────────────────────────┐
│     Streamlit Python Backend         │
│  - Forecasting logic                 │
│  - Data processing                   │
│  - Session management                │
└─────────────────────────────────────┘
            ↓ Generates
┌─────────────────────────────────────┐
│   Streamlit Default HTML/CSS/JS      │
│  - Basic widgets                     │
│  - Limited styling                   │
└─────────────────────────────────────┘
```

### New Hybrid Architecture
```
┌─────────────────────────────────────┐
│     Streamlit Python Backend         │
│  - Forecasting logic (unchanged)     │
│  - Data processing (unchanged)       │
│  - Session management (unchanged)    │
└─────────────────────────────────────┘
            ↓ Generates
┌─────────────────────────────────────┐
│   Streamlit Base + Custom Injection  │
│  ┌─────────────────────────────────┐│
│  │  shadcn Design System (CSS)     ││
│  │  - Tailwind CDN                 ││
│  │  - shadcn color tokens          ││
│  │  - shadcn component styles      ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │  Custom HTML Components         ││
│  │  - Chat bubbles                 ││
│  │  - Cards                        ││
│  │  - Buttons                      ││
│  │  - Tables                       ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

---

## 2. Design System - shadcn/ui Principles

### 2.1 Color Palette (shadcn/ui default)

Based on shadcn/ui's neutral slate theme:

```css
:root {
  /* Primary Colors */
  --background: 0 0% 100%;           /* White */
  --foreground: 222.2 84% 4.9%;      /* Slate 950 */

  /* Card & UI Elements */
  --card: 0 0% 100%;                 /* White */
  --card-foreground: 222.2 84% 4.9%; /* Slate 950 */

  /* Muted (Secondary) */
  --muted: 210 40% 96.1%;            /* Slate 100 */
  --muted-foreground: 215.4 16.3% 46.9%; /* Slate 500 */

  /* Accent */
  --accent: 210 40% 96.1%;           /* Slate 100 */
  --accent-foreground: 222.2 47.4% 11.2%; /* Slate 900 */

  /* Primary (Action) */
  --primary: 222.2 47.4% 11.2%;      /* Slate 900 */
  --primary-foreground: 210 40% 98%; /* Slate 50 */

  /* Borders */
  --border: 214.3 31.8% 91.4%;       /* Slate 200 */
  --input: 214.3 31.8% 91.4%;        /* Slate 200 */
  --ring: 222.2 84% 4.9%;            /* Slate 950 */

  /* Status Colors */
  --destructive: 0 84.2% 60.2%;      /* Red 500 */
  --destructive-foreground: 210 40% 98%;

  /* Radius */
  --radius: 0.5rem;                  /* 8px */
}

/* Dark mode (optional) */
.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  /* ... etc */
}
```

### 2.2 Typography

Using shadcn's recommended fonts:

```css
/* Font Families */
--font-sans: ui-sans-serif, system-ui, -apple-system, sans-serif;
--font-mono: ui-monospace, "Cascadia Code", monospace;

/* Font Sizes (Tailwind scale) */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */
--text-4xl: 2.25rem;   /* 36px */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 2.3 Spacing (Tailwind)

```css
/* Spacing Scale */
--spacing-1: 0.25rem;   /* 4px */
--spacing-2: 0.5rem;    /* 8px */
--spacing-3: 0.75rem;   /* 12px */
--spacing-4: 1rem;      /* 16px */
--spacing-6: 1.5rem;    /* 24px */
--spacing-8: 2rem;      /* 32px */
--spacing-12: 3rem;     /* 48px */
--spacing-16: 4rem;     /* 64px */
```

### 2.4 Shadows

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
```

---

## 3. Component Specifications

### 3.1 Chat Message (shadcn Card variant)

**Design:**
- Based on shadcn's Card component
- Rounded borders (var(--radius))
- Subtle shadow
- Border for definition
- Hover state with shadow lift

**HTML Structure:**
```html
<div class="chat-message user">
  <div class="message-avatar">U</div>
  <div class="message-content">
    <div class="message-text">Forecast Spring 2026</div>
    <div class="message-time">2:30 PM</div>
  </div>
</div>
```

**Styling (Tailwind classes):**
```css
.chat-message {
  @apply rounded-lg border bg-card text-card-foreground shadow-sm
         hover:shadow-md transition-shadow p-4 mb-3;
}

.chat-message.user {
  @apply ml-auto max-w-[80%] border-primary/20 bg-primary text-primary-foreground;
}

.chat-message.assistant {
  @apply mr-auto max-w-[80%];
}
```

### 3.2 Input Field (shadcn Input)

**Design:**
- Clean border
- Focus ring effect
- Proper padding
- Disabled states

**Tailwind Classes:**
```
flex h-10 w-full rounded-md border border-input bg-background px-3 py-2
text-sm ring-offset-background file:border-0 file:bg-transparent
file:text-sm file:font-medium placeholder:text-muted-foreground
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50
```

### 3.3 Button (shadcn Button variants)

**Primary Button:**
```
inline-flex items-center justify-center rounded-md text-sm font-medium
ring-offset-background transition-colors focus-visible:outline-none
focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground
hover:bg-primary/90 h-10 px-4 py-2
```

**Secondary Button:**
```
bg-secondary text-secondary-foreground hover:bg-secondary/80
```

**Outline Button:**
```
border border-input bg-background hover:bg-accent hover:text-accent-foreground
```

### 3.4 Card (Data Display)

**For forecast results, file upload areas:**

```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Forecast Results</h3>
    <p class="card-description">Spring 2026 enrollment predictions</p>
  </div>
  <div class="card-content">
    <!-- Table or content -->
  </div>
  <div class="card-footer">
    <!-- Actions -->
  </div>
</div>
```

**Tailwind Classes:**
```
.card {
  @apply rounded-lg border bg-card text-card-foreground shadow-sm;
}

.card-header {
  @apply flex flex-col space-y-1.5 p-6;
}

.card-title {
  @apply text-2xl font-semibold leading-none tracking-tight;
}

.card-description {
  @apply text-sm text-muted-foreground;
}

.card-content {
  @apply p-6 pt-0;
}

.card-footer {
  @apply flex items-center p-6 pt-0;
}
```

### 3.5 Table (shadcn Table)

**For forecast data display:**

```css
.table-container {
  @apply relative w-full overflow-auto;
}

table {
  @apply w-full caption-bottom text-sm;
}

thead {
  @apply [&_tr]:border-b;
}

tbody {
  @apply [&_tr:last-child]:border-0;
}

tr {
  @apply border-b transition-colors hover:bg-muted/50;
}

th {
  @apply h-12 px-4 text-left align-middle font-medium text-muted-foreground;
}

td {
  @apply p-4 align-middle;
}
```

### 3.6 Badge/Chip (Status indicators)

```
inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs
font-semibold transition-colors focus:outline-none focus:ring-2
focus:ring-ring focus:ring-offset-2 border-transparent bg-primary
text-primary-foreground hover:bg-primary/80
```

### 3.7 Alert/Toast (Messages)

**Success:**
```html
<div class="alert alert-success">
  <svg class="alert-icon"><!-- check icon --></svg>
  <div>
    <h5 class="alert-title">Success</h5>
    <div class="alert-description">Forecast generated successfully!</div>
  </div>
</div>
```

**Tailwind Classes:**
```css
.alert {
  @apply relative w-full rounded-lg border p-4;
}

.alert-success {
  @apply bg-green-50 text-green-900 border-green-200;
}

.alert-title {
  @apply mb-1 font-medium leading-none tracking-tight;
}

.alert-description {
  @apply text-sm opacity-90;
}
```

---

## 4. Implementation Strategy

### 4.1 Technology Stack

**Core:**
- Python 3.9+ (existing)
- Streamlit 1.28+ (existing)

**New Additions:**
- Tailwind CSS 3.4+ (CDN)
- Lucide Icons (CDN) - shadcn's icon library
- Alpine.js (optional, for micro-interactions)

**No Build Tools Required:**
- All CSS/JS loaded via CDN
- No npm, webpack, or vite
- Pure HTML/CSS/JS injection

### 4.2 File Structure

```
Forecast Tool/
├── app_chat.py                    # Main app (updated)
├── forecast_tool/
│   ├── ui/
│   │   ├── chat_window.py         # Updated with shadcn components
│   │   ├── output_window.py       # Updated with shadcn components
│   │   └── components/            # NEW: Reusable shadcn components
│   │       ├── __init__.py
│   │       ├── button.py          # shadcn Button component
│   │       ├── card.py            # shadcn Card component
│   │       ├── input.py           # shadcn Input component
│   │       ├── table.py           # shadcn Table component
│   │       ├── alert.py           # shadcn Alert component
│   │       └── badge.py           # shadcn Badge component
│   └── styles/                    # NEW: Style utilities
│       ├── __init__.py
│       ├── shadcn_tokens.py       # CSS variables/tokens
│       └── tailwind_config.py     # Tailwind configuration
└── static/                        # NEW: Static assets (optional)
    └── icons/
```

### 4.3 Implementation Approach

**Method 1: CSS Override (Recommended)**
- Inject Tailwind CSS + shadcn tokens via `st.markdown()`
- Override Streamlit's default styles
- Use Tailwind utility classes on Streamlit components
- Fast, no custom components needed

**Method 2: Custom HTML Components**
- Create Python functions that return HTML strings
- Use `st.markdown(..., unsafe_allow_html=True)`
- More control, but more code

**Method 3: Streamlit Custom Components (Advanced)**
- Create true custom components with React
- Most powerful, but requires build step
- Not recommended for "quick" timeline

**Chosen: Hybrid of Method 1 + Method 2**
- Use Method 1 for base styling
- Use Method 2 for chat messages, cards, complex layouts
- Keep it simple and maintainable

---

## 5. Component Python Helpers

### 5.1 Button Component

```python
# forecast_tool/ui/components/button.py

def button(label: str, variant: str = "default", onclick: str = None,
           icon: str = None, full_width: bool = False) -> str:
    """
    Generate shadcn-styled button HTML

    Args:
        label: Button text
        variant: 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive'
        onclick: JavaScript onclick handler
        icon: Lucide icon name
        full_width: If True, button spans full width

    Returns:
        HTML string for button
    """
    variant_classes = {
        'default': 'bg-primary text-primary-foreground hover:bg-primary/90',
        'secondary': 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        'outline': 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        'ghost': 'hover:bg-accent hover:text-accent-foreground',
        'destructive': 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
    }

    base_classes = "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2"

    width_class = "w-full" if full_width else ""
    classes = f"{base_classes} {variant_classes.get(variant, variant_classes['default'])} {width_class}"

    icon_html = f'<i data-lucide="{icon}" class="mr-2 h-4 w-4"></i>' if icon else ''
    onclick_attr = f'onclick="{onclick}"' if onclick else ''

    return f'''
    <button class="{classes}" {onclick_attr}>
        {icon_html}
        {label}
    </button>
    '''
```

### 5.2 Card Component

```python
# forecast_tool/ui/components/card.py

def card(title: str = None, description: str = None,
         content: str = "", footer: str = None) -> str:
    """
    Generate shadcn-styled card HTML

    Args:
        title: Card title
        description: Card description
        content: Main card content (HTML)
        footer: Footer content (HTML)

    Returns:
        HTML string for card
    """
    header_html = ""
    if title or description:
        title_html = f'<h3 class="text-2xl font-semibold leading-none tracking-tight">{title}</h3>' if title else ''
        desc_html = f'<p class="text-sm text-muted-foreground">{description}</p>' if description else ''
        header_html = f'''
        <div class="flex flex-col space-y-1.5 p-6">
            {title_html}
            {desc_html}
        </div>
        '''

    footer_html = f'<div class="flex items-center p-6 pt-0">{footer}</div>' if footer else ''

    return f'''
    <div class="rounded-lg border bg-card text-card-foreground shadow-sm">
        {header_html}
        <div class="p-6 pt-0">
            {content}
        </div>
        {footer_html}
    </div>
    '''
```

### 5.3 Chat Message Component

```python
# forecast_tool/ui/components/chat_message.py

def chat_message(message: str, role: str = "user", timestamp: str = None) -> str:
    """
    Generate shadcn-styled chat message bubble

    Args:
        message: Message text
        role: 'user' | 'assistant'
        timestamp: Optional timestamp string

    Returns:
        HTML string for chat message
    """
    is_user = role == "user"

    avatar_class = "bg-primary text-primary-foreground" if is_user else "bg-secondary text-secondary-foreground"
    avatar_initial = "U" if is_user else "A"

    align_class = "ml-auto" if is_user else "mr-auto"
    bg_class = "bg-primary text-primary-foreground" if is_user else "bg-card"

    timestamp_html = f'<div class="text-xs opacity-70 mt-1">{timestamp}</div>' if timestamp else ''

    return f'''
    <div class="flex gap-3 mb-4 max-w-[80%] {align_class}">
        <div class="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full {avatar_class} text-sm font-medium">
            {avatar_initial}
        </div>
        <div class="rounded-lg border {bg_class} shadow-sm p-4 flex-1">
            <div class="text-sm">{message}</div>
            {timestamp_html}
        </div>
    </div>
    '''
```

### 5.4 Table Component

```python
# forecast_tool/ui/components/table.py

def table(df, headers: list = None) -> str:
    """
    Generate shadcn-styled table from DataFrame

    Args:
        df: Pandas DataFrame
        headers: Optional custom headers

    Returns:
        HTML string for table
    """
    if headers is None:
        headers = df.columns.tolist()

    header_row = "".join([
        f'<th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">{h}</th>'
        for h in headers
    ])

    rows = []
    for _, row in df.iterrows():
        cells = "".join([
            f'<td class="p-4 align-middle">{val}</td>'
            for val in row
        ])
        rows.append(f'<tr class="border-b transition-colors hover:bg-muted/50">{cells}</tr>')

    return f'''
    <div class="relative w-full overflow-auto rounded-lg border">
        <table class="w-full caption-bottom text-sm">
            <thead class="border-b">
                <tr>{header_row}</tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    '''
```

---

## 6. Base Styling Template

### 6.1 Main CSS Injection (app_chat.py)

```python
# In app_chat.py

st.markdown("""
<style>
    /* ========================================
       shadcn/ui Design System for Streamlit
       ======================================== */

    /* Import Tailwind CSS */
    @import url('https://cdn.jsdelivr.net/npm/tailwindcss@3.4.1/base.min.css');

    /* CSS Variables - shadcn tokens */
    :root {
        --background: 0 0% 100%;
        --foreground: 222.2 84% 4.9%;

        --card: 0 0% 100%;
        --card-foreground: 222.2 84% 4.9%;

        --popover: 0 0% 100%;
        --popover-foreground: 222.2 84% 4.9%;

        --primary: 222.2 47.4% 11.2%;
        --primary-foreground: 210 40% 98%;

        --secondary: 210 40% 96.1%;
        --secondary-foreground: 222.2 47.4% 11.2%;

        --muted: 210 40% 96.1%;
        --muted-foreground: 215.4 16.3% 46.9%;

        --accent: 210 40% 96.1%;
        --accent-foreground: 222.2 47.4% 11.2%;

        --destructive: 0 84.2% 60.2%;
        --destructive-foreground: 210 40% 98%;

        --border: 214.3 31.8% 91.4%;
        --input: 214.3 31.8% 91.4%;
        --ring: 222.2 84% 4.9%;

        --radius: 0.5rem;
    }

    /* Apply to body */
    * {
        border-color: hsl(var(--border));
    }

    body {
        background-color: hsl(var(--background));
        color: hsl(var(--foreground));
        font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
    }

    /* Override Streamlit defaults */
    .main {
        background-color: hsl(var(--background));
        padding: 1.5rem;
    }

    /* Chat Messages */
    .stChatMessage {
        border-radius: var(--radius);
        border: 1px solid hsl(var(--border));
        background: hsl(var(--card));
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        padding: 1rem;
        margin-bottom: 0.75rem;
    }

    /* Buttons */
    .stButton button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius);
        font-size: 0.875rem;
        font-weight: 500;
        transition: all 0.2s;
        background: hsl(var(--primary));
        color: hsl(var(--primary-foreground));
        padding: 0.5rem 1rem;
        height: 2.5rem;
    }

    .stButton button:hover {
        background: hsl(var(--primary) / 0.9);
    }

    /* Input Fields */
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox select {
        border-radius: var(--radius);
        border: 1px solid hsl(var(--input));
        background: hsl(var(--background));
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        height: 2.5rem;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stSelectbox select:focus {
        outline: none;
        ring: 2px;
        ring-color: hsl(var(--ring));
        ring-offset: 2px;
    }

    /* Cards/Expanders */
    div[data-testid="stExpander"] {
        border-radius: var(--radius);
        border: 1px solid hsl(var(--border));
        background: hsl(var(--card));
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    }

    /* Data Tables */
    .stDataFrame {
        border-radius: var(--radius);
        border: 1px solid hsl(var(--border));
        overflow: hidden;
    }

    .stDataFrame thead th {
        background: hsl(var(--muted));
        color: hsl(var(--muted-foreground));
        font-weight: 500;
        text-transform: none;
        padding: 0.75rem 1rem;
    }

    .stDataFrame tbody tr {
        border-bottom: 1px solid hsl(var(--border));
    }

    .stDataFrame tbody tr:hover {
        background: hsl(var(--muted) / 0.5);
    }

    .stDataFrame tbody td {
        padding: 0.75rem 1rem;
    }
</style>

<!-- Load Lucide Icons -->
<script src="https://unpkg.com/lucide@latest"></script>
<script>
    // Initialize Lucide icons
    document.addEventListener('DOMContentLoaded', () => {
        lucide.createIcons();
    });

    // Re-initialize on Streamlit rerun
    document.addEventListener('streamlit:render', () => {
        lucide.createIcons();
    });
</script>
""", unsafe_allow_html=True)
```

---

## 7. Implementation Phases

### Phase 1: Setup & Base Styling (Day 1)
**Tasks:**
1. Add Tailwind CSS CDN to app_chat.py
2. Define shadcn CSS variables
3. Create component helper module structure
4. Apply base shadcn styling to existing Streamlit components

**Deliverables:**
- Updated app_chat.py with shadcn tokens
- forecast_tool/ui/components/ package created
- Basic shadcn styling applied

**Success Criteria:**
- App loads with new color scheme
- Buttons have shadcn styling
- Tables have shadcn styling

### Phase 2: Chat Interface (Day 2)
**Tasks:**
1. Create chat_message() component
2. Update chat_window.py to use shadcn messages
3. Style chat input field
4. Add message timestamps
5. Implement smooth animations

**Deliverables:**
- Redesigned chat window with shadcn cards
- Animated message appearance
- Styled chat input

**Success Criteria:**
- Chat messages look like shadcn cards
- Smooth fade-in animations
- Proper user/assistant styling

### Phase 3: Data Display (Day 3)
**Tasks:**
1. Create table() component
2. Create card() component
3. Update output_window.py with cards
4. Style file upload area
5. Add forecast result cards

**Deliverables:**
- shadcn-styled tables
- Card-based layout for results
- Improved file upload UI

**Success Criteria:**
- Forecast results display in clean cards
- Tables have hover effects
- Upload area is inviting

### Phase 4: Controls & Actions (Day 4)
**Tasks:**
1. Create button() component with variants
2. Create alert() component
3. Update sidebar styling
4. Add loading states
5. Implement toast notifications

**Deliverables:**
- shadcn button variants
- Alert/toast components
- Styled sidebar
- Loading indicators

**Success Criteria:**
- All buttons match shadcn design
- Alerts are clear and accessible
- Loading states are smooth

### Phase 5: Polish & Testing (Day 5)
**Tasks:**
1. Add micro-interactions
2. Optimize performance
3. Test all workflows
4. Fix edge cases
5. Create user documentation

**Deliverables:**
- Polished animations
- Performance optimizations
- Test report
- Updated QUICKSTART

**Success Criteria:**
- No visual bugs
- Smooth 60fps animations
- All features working
- Documentation complete

---

## 8. Deployment Plan

### 8.1 Requirements

**No changes to deployment:**
- Same Streamlit deployment
- No build step needed
- All assets loaded via CDN
- Python-only backend

**Updated files:**
- app_chat.py (styling)
- forecast_tool/ui/*.py (components)
- forecast_tool/ui/components/*.py (new helpers)

### 8.2 Deployment Steps

1. **Testing:**
   ```bash
   streamlit run app_chat.py
   ```

2. **Production:**
   - Same launcher script works
   - Same Docker container (if used)
   - Same Streamlit Cloud deployment (if used)

3. **Rollback:**
   - Keep backup of old app_chat.py
   - Can revert instantly if issues

### 8.3 Browser Compatibility

**Supported:**
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

**CDN Dependencies:**
- Tailwind CSS (jsdelivr)
- Lucide Icons (unpkg)
- Both have 99.9% uptime

---

## 9. Maintenance & Extensibility

### 9.1 Adding New Components

**Process:**
1. Create Python helper in `forecast_tool/ui/components/`
2. Follow shadcn component structure
3. Use Tailwind utility classes
4. Add to components/__init__.py

**Example - New Alert Component:**

```python
# forecast_tool/ui/components/alert.py

def alert(title: str, description: str, variant: str = "default") -> str:
    """Generate shadcn Alert component"""

    variant_classes = {
        'default': 'bg-background text-foreground',
        'destructive': 'border-destructive/50 text-destructive dark:border-destructive'
    }

    return f'''
    <div class="relative w-full rounded-lg border p-4 {variant_classes[variant]}">
        <h5 class="mb-1 font-medium leading-none tracking-tight">{title}</h5>
        <div class="text-sm opacity-90">{description}</div>
    </div>
    '''
```

### 9.2 Updating Design Tokens

**To change color scheme:**
1. Update CSS variables in app_chat.py
2. Use shadcn theme generator: https://ui.shadcn.com/themes
3. Copy generated CSS variables
4. Paste into :root {} block

**No code changes needed** - all components use CSS variables.

### 9.3 Future Enhancements

**Easy additions:**
- Dark mode toggle (add .dark class)
- Additional shadcn components (dropdown, dialog, etc.)
- Custom animations (CSS only)
- Themed variants (different color schemes)

**Medium additions:**
- Custom Streamlit component for true React integration
- Charting library with shadcn styling
- Advanced form validation

---

## 10. Risk Assessment

### Low Risk ✅
- **CSS-only changes** - No backend logic affected
- **CDN reliability** - jsdelivr/unpkg have >99.9% uptime
- **Browser support** - Tailwind works on all modern browsers
- **Performance** - CSS is lightweight (<50KB)
- **Rollback** - Can revert instantly

### Medium Risk ⚠️
- **Learning curve** - Team needs to learn Tailwind classes
- **Consistency** - Must follow shadcn patterns
- **Custom components** - Need to maintain Python helpers

### Mitigation
- **Documentation** - Comprehensive component guide
- **Examples** - Clear code examples for each component
- **Testing** - Thorough testing before deployment
- **Backup** - Keep old design as fallback

---

## 11. Success Metrics

### Visual Quality
- [ ] Matches shadcn/ui design system
- [ ] Consistent spacing and typography
- [ ] Smooth animations (60fps)
- [ ] Accessible (WCAG AA)

### User Experience
- [ ] Faster perceived load time
- [ ] Clearer visual hierarchy
- [ ] More intuitive interactions
- [ ] Professional appearance

### Technical
- [ ] No performance regression
- [ ] No new dependencies beyond CDN
- [ ] Same deployment process
- [ ] Easy to maintain

### Timeline
- [ ] Completed in 5 days or less
- [ ] Production-ready
- [ ] Documentation complete

---

## 12. Comparison: Before vs. After

### Before (Current)
- Default Streamlit styling
- Basic chat interface
- Minimal visual hierarchy
- Generic appearance
- Limited custom styling

### After (shadcn)
- shadcn/ui design system
- Card-based chat messages
- Clear visual hierarchy
- Professional, modern appearance
- Comprehensive component library

### What Stays the Same
- Python backend
- Forecasting logic
- Data processing
- Deployment method
- One-click launcher
- All functionality

### What Changes
- Visual design
- Component structure (HTML)
- CSS styling
- User interface polish

---

## 13. Open Questions

1. **Dark mode**: Include or launch without it?
   - Recommendation: Launch without, add later if needed

2. **Icons**: Use Lucide (shadcn default) or alternative?
   - Recommendation: Lucide via CDN (simple, matches shadcn)

3. **Animations**: How much motion?
   - Recommendation: Subtle (respect prefers-reduced-motion)

4. **Custom components**: Build any true React components?
   - Recommendation: No, keep it CSS/HTML only for speed

5. **Documentation**: How detailed?
   - Recommendation: User guide + developer component docs

---

## 14. Approval Checklist

Before proceeding with implementation:

- [ ] Architecture approved (Hybrid Streamlit + shadcn CSS)
- [ ] Timeline acceptable (5 days)
- [ ] Component specs approved
- [ ] Design tokens approved (can customize colors)
- [ ] No dark mode initially (OK?)
- [ ] CDN approach approved (no build step)
- [ ] Risk assessment reviewed
- [ ] Success criteria agreed upon

---

## 15. Next Steps

**Once approved:**

1. **Day 1**: Setup base styling and tokens
2. **Day 2**: Redesign chat interface
3. **Day 3**: Update data display components
4. **Day 4**: Polish controls and actions
5. **Day 5**: Testing and documentation

**Deliverables:**
- Working shadcn-styled interface
- Component library
- Updated documentation
- Test report

**Questions or changes?** This spec is a living document - we can adjust before implementation.

---

**Document Version:** 1.0
**Created:** 2026-01-29
**Author:** Claude Code
**Status:** Awaiting Approval
