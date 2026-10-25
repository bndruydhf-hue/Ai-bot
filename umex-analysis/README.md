# UMEX Trading Platform - UI Design Analysis

Complete reverse engineering analysis of https://app.umex.com/trade/SPARK

## 📁 Repository Structure

```
umex-analysis/
├── README.md                          # This file
├── design-system/
│   ├── colors.css                     # Complete CSS custom properties
│   ├── spacing.css                    # Spacing scale
│   ├── typography.css                 # Typography scale
│   └── themes.css                     # Dark/light theme definitions
├── components/
│   ├── core/                          # Core UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Switch.tsx
│   │   ├── Tabs.tsx
│   │   ├── Dialog.tsx
│   │   ├── Tooltip.tsx
│   │   ├── Avatar.tsx
│   │   ├── Badge.tsx
│   │   ├── Skeleton.tsx
│   │   └── Toast.tsx
│   ├── trading/                       # Trading-specific components
│   │   ├── AssetQuote.tsx
│   │   ├── TradePanel.tsx
│   │   ├── ChartDrawingTools.tsx
│   │   ├── DealAdjustments.tsx
│   │   ├── StockPositionDialog.tsx
│   │   └── SocialTrading.tsx
│   ├── layout/                        # Layout components
│   │   ├── MobileShell.tsx
│   │   ├── DesktopShell.tsx
│   │   ├── Header.tsx
│   │   ├── TabBar.tsx
│   │   └── Sidebar.tsx
│   └── data-display/                  # Data display components
│       ├── DataTable.tsx
│       ├── PriceChart.tsx
│       └── OrderBook.tsx
├── architecture/
│   ├── stores/                        # State management (Zustand pattern)
│   │   ├── useAssetsStore.ts
│   │   ├── useTradingStore.ts
│   │   ├── useUserStore.ts
│   │   └── useWebSocketStore.ts
│   ├── websocket/                     # WebSocket management
│   │   ├── WebSocketManager.ts
│   │   └── multi-region.ts
│   └── routing/                       # Route definitions
│       └── routes.ts
├── assets/
│   ├── extracted/                     # Extracted from production
│   │   ├── index-D4kpDWzq.css         # Full compiled CSS
│   │   ├── early-BkGKw6zE.js          # Early initialization script
│   │   ├── index-p-gSNpv2.js          # Main JS bundle (minified)
│   │   ├── route-SKMbobf2.js          # Trading route bundle
│   │   ├── MobileShell-BupRUu_R.js    # Mobile shell bundle
│   │   └── DesktopShell-Ca7wf2Mc.js   # Desktop shell bundle
│   └── source-maps/                   # Source maps for debugging
├── docs/
│   ├── DESIGN_SYSTEM.md               # Design system documentation
│   ├── COMPONENT_LIBRARY.md           # Component API docs
│   ├── ARCHITECTURE.md                # Technical architecture
│   ├── WEBSOCKET_PROTOCOL.md          # WebSocket message formats
│   └── API_ENDPOINTS.md               # REST API endpoints
├── scripts/
│   ├── extract-assets.js              # Asset extraction script
│   ├── generate-design-tokens.js      # Design token generator
│   └── analyze-bundle.js              # Bundle analyzer
└── package.json                       # Development dependencies
```

## 🎨 Design System Summary

### Core Colors
```css
--app-text-primary: #35a7ff        /* Primary brand blue */
--theme-color: #080b16             /* Dark background */
--plot-candle-up: #0e8f5e          /* Bullish green */
--plot-candle-down: #c64547        /* Bearish red */
--system-text-success: #13bf7d     /* Success */
--system-text-error: #ff595c       /* Error */
```

### Surface Hierarchy (4 levels)
- Level 1: `#16212e` (deepest)
- Level 2: `#1f2a37`
- Level 3: `#2a3846`
- Level 4: `#354553` (highest)

### Glassmorphism
```css
backdrop-filter: blur(24px);
background: rgba(22, 33, 46, 0.8);
border: 1px solid #ffffff1f;
```

## 🏗️ Architecture Highlights

- **Framework**: React 18 + TypeScript + Vite
- **State**: Zustand-like custom stores with selectors
- **Real-time**: Multi-region WebSocket (EU, SG, US, IN)
- **Styling**: CSS Modules + CSS Custom Properties
- **Analytics**: Sentry, GTM, Microsoft Clarity
- **Security**: reCAPTCHA v2/v3, secure cookies

## 📱 Dual Shell Architecture

| Platform | Shell Component | Key Features |
|----------|----------------|--------------|
| Mobile | `MobileShell` | Bottom tab bar (5 tabs), hamburger menu |
| Desktop | `DesktopShell` | Top bar, side toolbar, multi-panel |

## 🔧 Quick Start

```bash
# Install dependencies
npm install

# Generate design tokens from extracted CSS
npm run generate:tokens

# Start development server
npm run dev

# Analyze production bundle
npm run analyze
```

## 📊 Extracted Assets

All production assets have been extracted and de-obfuscated where possible:
- **CSS**: 21KB+ of design tokens and component styles
- **JS Bundles**: 5+ major chunks analyzed
- **Source Maps**: Available for debugging
- **WebSocket Protocol**: Documented message formats

## 📝 License

Internal analysis - not for redistribution.