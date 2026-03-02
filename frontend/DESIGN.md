## Design Schema

### Reference

Design mockup: `/Users/rs/Documents/proj/oad/frontend/OAD_design.png`

### Pages

| Page | Purpose | Entry Point |
|------|---------|-------------|
| Dashboard | Daily lead cards, voting, date navigation | `/` (default) |
| Algorithm | Natural language interest config, tag wordcloud | Write button (bottom-right) |

### Dashboard

#### Layout

- Header: "today is the day" + hamburger menu
- Body: 3 lead cards in horizontal row
- Footer: Date display (opens picker), write button

#### Lead Card
```
┌─────────────────────────┐
│ ☆                       │  ← Favorite toggle
│                         │
│ name                    │  ← Lead.name (bold)
│ details                 │  ← Lead.title + Lead.affiliation
│                         │
│                         │
│ contact | source        │  ← contact_hint link | source_type badge
│                         │
│ 👍   ☀   👎             │  ← Upvote, neutral, downvote
└─────────────────────────┘
```

#### Interactions

| Element | Action | Effect |
|---------|--------|--------|
| Date display | Tap | Opens month picker |
| Date picker | Select date | Loads leads for that date |
| Upvote (👍) | Tap | +weight to lead's matched tags |
| Downvote (👎) | Tap | -weight to lead's matched tags |
| Favorite (☆) | Tap | Toggles `Lead.favorited` |
| Write button | Tap | Navigate to Algorithm page |

### Algorithm Page

#### Layout

- Header: "today is the day" + hamburger menu
- Body: Wordcloud visualization (tags sized by weight)
- Footer: Natural language input, date display, back button

#### Wordcloud

- Each tag from `InterestConfig` rendered
- Size proportional to `InterestConfig.weight`
- Interactive: tap tag to view/edit

#### Natural Language Input
```
┌─────────────────────────────────────────┐
│ What would you like to know?            │
│                                         │
│ 🖼  </>  🎤                         ↑   │
└─────────────────────────────────────────┘
```

- Text input parsed by model → generates/updates `InterestConfig` entries

### Data Flow
```
User votes on card
        │
        ▼
Extract matched InterestConfig.keyword(s) from Lead
        │
        ▼
Adjust InterestConfig.weight (+0.1 upvote, -0.1 downvote)
        │
        ▼
Wordcloud re-renders with new sizes
```

### New Fields Required

| Model | Field | Type | Purpose |
|-------|-------|------|---------|
| `Lead` | `favorited` | `bool` | User bookmark |
| `Lead` | `vote` | `int` | -1, 0, +1 |
| `Lead` | `matched_interests` | `list[int]` | FK to InterestConfig IDs used in scoring |

### Component Mapping

| Design Element | Component |
|----------------|-----------|
| Lead card | `LeadCard.tsx` |
| Card row | `LeadCardRow.tsx` |
| Date picker | `DatePicker.tsx` |
| Wordcloud | `TagCloud.tsx` |
| NL input | `AlgorithmInput.tsx` |

### Design Tokens — Paper Theme
```css
:root {
  /* Base paper tones */
  --paper-white: #faf9f6;       /* page background */
  --paper-cream: #f5f3ee;       /* card background */
  --paper-tan: #ebe7df;         /* card hover, input bg */
  --paper-kraft: #d9d3c7;       /* borders, dividers */
  
  /* Ink tones */
  --ink-black: #2c2c2c;         /* primary text */
  --ink-gray: #5c5c5c;          /* secondary text */
  --ink-light: #8c8c8c;         /* tertiary, placeholders */
  --ink-faint: #b5b5b5;         /* disabled states */
  
  /* Accent — muted green (edited from date picker) */
  --accent: #4e6c4e;
  --accent-soft: #b2dfa1;
  --accent-bg: #f0edf5;
  
  /* Feedback */
  --upvote: #5a7c5a;            /* muted green */
  --downvote: #9c6b6b;          /* muted red */
  
  /* Elevation */
  --shadow-card: 0 1px 3px rgba(44, 44, 44, 0.08);
  --shadow-hover: 0 3px 8px rgba(44, 44, 44, 0.12);
  --shadow-picker: 0 4px 16px rgba(44, 44, 44, 0.15);
  
  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  
  /* Typography */
  --font-display: 'Instrument Serif', Georgia, serif;
  --font-body: 'Inter', -apple-system, sans-serif;
}
```

### Implementation Notes

- Page background: `--paper-white`
- Cards: `--paper-cream` with `--shadow-card`, `--radius-lg`
- Card hover: lighten to `--paper-tan` border or subtle `--shadow-hover`
- Text: `--ink-black` for names, `--ink-gray` for details
- Buttons/icons: `--ink-light` default, `--ink-black` on hover
- Date picker: `--paper-cream` bg, `--accent` for selected date
- Voting debounced 300ms; optimistic UI updates
- Wordcloud updates optimistically, reconciles on API response