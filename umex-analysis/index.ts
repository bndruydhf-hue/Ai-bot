/**
 * UMEX UI Analysis - Main Entry Point
 * Export all design system tokens, components, and utilities
 */

// Design System
export * from './design-system/colors';
export * from './design-system/chart-colors';
export * from './design-system/surface-colors';
export * from './design-system/effects';
export * from './design-system/themes';
export * from './design-system/spacing';
export * from './design-system/typography';

// Components
export { Button } from './components/core/Button';
export { Switch } from './components/core/Switch';

// Stores
export { useAssetsStore, selectAssets, selectGroups, selectSelectedAsset, selectFilteredAssets } from './architecture/stores/useAssetsStore';
export { useTradingStore, selectCurrentDeal, selectChartDrawings, selectOpenDeals, selectClosedDeals } from './architecture/stores/useTradingStore';

// WebSocket
export { WebSocketManager, createWebSocketManager, type WebSocketManagerConfig, type ConnectionState, type WebSocketMessage } from './architecture/websocket/WebSocketManager';

// Types
export type {
  Asset,
  AssetGroup,
  Deal,
  ChartDrawing,
  TraderDeal,
  TradeType,
  TradeDirection,
  DealStatus,
} from './architecture/stores/useTradingStore';