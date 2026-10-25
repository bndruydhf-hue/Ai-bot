/**
 * UMEX Assets Store
 * Zustand-like pattern extracted from production: useAssetsSelectList-DN_mc-eL.js
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

// ============================================
// TYPES
// ============================================

export interface Asset {
  id: string | number;
  symbol: string;
  name: string;
  type: 'FTT' | 'STOCK' | 'CRYPTO' | 'FOREX' | 'COMMODITY';
  icon: string;
  isActive: boolean;
  group: string;
  minAmount: number;
  maxAmount: number;
  payout: number;
  change24h: number;
  price: number;
}

export interface AssetGroup {
  id: string;
  name: string;
  assets: Asset[];
  isExpanded: boolean;
}

export interface AssetsState {
  // State
  assets: Asset[];
  groups: AssetGroup[];
  selectedAssetId: string | number | null;
  selectedGroupId: string | null;
  searchQuery: string;
  isLoading: boolean;
  error: string | null;

  // Favorites
  favoriteAssetIds: Set<string | number>;

  // Filters
  filterType: Asset['type'] | 'ALL';
  filterGroup: string | 'ALL';
  showFavoritesOnly: boolean;

  // Actions
  setAssets: (assets: Asset[]) => void;
  setGroups: (groups: AssetGroup[]) => void;
  selectAsset: (assetId: string | number | null) => void;
  selectGroup: (groupId: string | null) => void;
  setSearchQuery: (query: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Favorites
  toggleFavorite: (assetId: string | number) => void;
  isFavorite: (assetId: string | number) => boolean;

  // Filters
  setFilterType: (type: Asset['type'] | 'ALL') => void;
  setFilterGroup: (group: string | 'ALL') => void;
  setShowFavoritesOnly: (show: boolean) => void;

  // Computed
  getFilteredAssets: () => Asset[];
  getAssetById: (id: string | number) => Asset | undefined;
}

// ============================================
// STORE
// ============================================

export const useAssetsStore = create<AssetsState>()(
  subscribeWithSelector((set, get) => ({
    // Initial State
    assets: [],
    groups: [],
    selectedAssetId: null,
    selectedGroupId: null,
    searchQuery: '',
    isLoading: false,
    error: null,
    favoriteAssetIds: new Set(),
    filterType: 'ALL',
    filterGroup: 'ALL',
    showFavoritesOnly: false,

    // Actions
    setAssets: (assets) => set({ assets }),
    setGroups: (groups) => set({ groups }),
    selectAsset: (assetId) => set({ selectedAssetId: assetId }),
    selectGroup: (groupId) => set({ selectedGroupId: groupId }),
    setSearchQuery: (query) => set({ searchQuery: query }),
    setLoading: (loading) => set({ isLoading: loading }),
    setError: (error) => set({ error }),

    // Favorites
    toggleFavorite: (assetId) =>
      set((state) => {
        const newFavorites = new Set(state.favoriteAssetIds);
        if (newFavorites.has(assetId)) {
          newFavorites.delete(assetId);
        } else {
          newFavorites.add(assetId);
        }
        return { favoriteAssetIds: newFavorites };
      }),

    isFavorite: (assetId) => get().favoriteAssetIds.has(assetId),

    // Filters
    setFilterType: (type) => set({ filterType: type }),
    setFilterGroup: (group) => set({ filterGroup: group }),
    setShowFavoritesOnly: (show) => set({ showFavoritesOnly: show }),

    // Computed
    getFilteredAssets: () => {
      const { assets, searchQuery, filterType, filterGroup, showFavoritesOnly, favoriteAssetIds } = get();

      return assets.filter((asset) => {
        // Search filter
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          const matchesSymbol = asset.symbol.toLowerCase().includes(query);
          const matchesName = asset.name.toLowerCase().includes(query);
          if (!matchesSymbol && !matchesName) return false;
        }

        // Type filter
        if (filterType !== 'ALL' && asset.type !== filterType) return false;

        // Group filter
        if (filterGroup !== 'ALL' && asset.group !== filterGroup) return false;

        // Favorites filter
        if (showFavoritesOnly && !favoriteAssetIds.has(asset.id)) return false;

        return true;
      });
    },

    getAssetById: (id) => get().assets.find((a) => a.id === id),
  }))
);

// ============================================
// SELECTORS (for performance)
// ============================================

export const selectAssets = (state: AssetsState) => state.assets;
export const selectGroups = (state: AssetsState) => state.groups;
export const selectSelectedAsset = (state: AssetsState) =>
  state.assets.find((a) => a.id === state.selectedAssetId);
export const selectFilteredAssets = (state: AssetsState) => state.getFilteredAssets();
export const selectIsLoading = (state: AssetsState) => state.isLoading;
export const selectError = (state: AssetsState) => state.error;