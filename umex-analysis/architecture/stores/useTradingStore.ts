/**
 * UMEX Trading Store - Part 1: Types & Initial State
 * Zustand-like pattern extracted from production: route-SKMbobf2.js
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

// ============================================
// TYPES
// ============================================

export type TradeType = 'FTT' | 'STOCK' | 'PREDICTION';
export type TradeDirection = 'CALL' | 'PUT';
export type DealStatus = 'OPEN' | 'CLOSED' | 'CANCELLED' | 'EXPIRED';

export interface Deal {
  id: string;
  assetId: string | number;
  assetSymbol: string;
  assetName: string;
  type: TradeType;
  direction: TradeDirection;
  amount: number;
  entryPrice: number;
  currentPrice: number;
  payout: number;
  profit: number;
  status: DealStatus;
  openTime: number;
  closeTime?: number;
  expiryTime: number;
  isDemo: boolean;
}

export interface ChartDrawing {
  id: string;
  type: 'pencil' | 'line' | 'horizontal' | 'vertical' | 'trend' | 'fibonacci';
  color: string;
  width: number;
  points: { x: number; y: number; time: number; price: number }[];
  assetId: string | number;
  createdAt: number;
}

export interface TraderDeal {
  id: string;
  traderId: string;
  traderName: string;
  traderAvatar?: string;
  assetId: string | number;
  direction: TradeDirection;
  amount: number;
  profit: number;
  isWin: boolean;
  timestamp: number;
}

// ============================================
// STATE INTERFACE
// ============================================

export interface TradingState {
  // Current Trade Setup
  selectedAssetId: string | number | null;
  tradeType: TradeType;
  direction: TradeDirection;
  amount: number;
  expiryTime: number;
  isDemo: boolean;

  // Chart
  chartDrawings: ChartDrawing[];
  activeDrawingTool: ChartDrawing['type'] | null;
  drawingColor: string;
  drawingWidth: number;
  isDrawing: boolean;

  // Deals
  deals: Deal[];
  openDeals: Deal[];
  closedDeals: Deal[];
  dealHistory: Deal[];

  // Social Trading
  traderDeals: TraderDeal[];
  followedTraders: Set<string>;
  isSocialTradingEnabled: boolean;

  // UI State
  isTradePanelOpen: boolean;
  tradePanelVariant: 'mobile' | 'desktop-ftt' | 'desktop-stocks';
  showDealAdjustments: boolean;

  // Win Streak
  currentWinStreak: number;
  maxWinStreak: number;
}