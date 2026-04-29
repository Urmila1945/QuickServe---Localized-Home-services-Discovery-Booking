import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ── Types ──────────────────────────────────────────────────────────────

export type AssetCategory = 'hvac' | 'electrical' | 'plumbing' | 'appliance' | 'other';
export type KeyType = 'lockbox' | 'pin' | 'smartlock' | 'instructions';

export interface HomeAsset {
  id: string;
  name: string;
  category: AssetCategory;
  model: string;
  brand: string;
  installDate: string;
  warrantyExpiry: string;
  lastServiceDate: string;
  notes: string;
}

export interface PaintColor {
  id: string;
  room: string;
  color: string;
  brand: string;
  code: string;
}

export interface HomeProfile {
  squareFootage: string;
  bedrooms: string;
  bathrooms: string;
  yearBuilt: string;
  hvacModel: string;
  roofType: string;
  parkingType: string;
  assets: HomeAsset[];
  paintColors: PaintColor[];
}

export interface KeyEntry {
  id: string;
  label: string;
  code: string;
  type: KeyType;
  expiresAt: string;
  bookingId?: string;
  providerName?: string;
  createdAt: string;
  isActive: boolean;
  instructions: string;
}

// ── Store ──────────────────────────────────────────────────────────────

interface CustomerStore {
  homeProfile: HomeProfile;
  keyVault: KeyEntry[];
  joinedBlockParties: string[];

  updateHomeProfile: (fields: Partial<HomeProfile>) => void;

  addAsset: (asset: Omit<HomeAsset, 'id'>) => void;
  removeAsset: (id: string) => void;

  addPaintColor: (paint: Omit<PaintColor, 'id'>) => void;
  removePaintColor: (id: string) => void;

  addKeyEntry: (entry: Omit<KeyEntry, 'id' | 'createdAt'>) => void;
  removeKeyEntry: (id: string) => void;
  toggleKeyActive: (id: string) => void;

  joinBlockParty: (partyId: string) => void;
}

const defaultProfile: HomeProfile = {
  squareFootage: '',
  bedrooms: '',
  bathrooms: '',
  yearBuilt: '',
  hvacModel: '',
  roofType: '',
  parkingType: '',
  assets: [],
  paintColors: [],
};

export const useCustomerStore = create<CustomerStore>()(
  persist(
    (set) => ({
      homeProfile: defaultProfile,
      keyVault: [],
      joinedBlockParties: [],

      updateHomeProfile: (fields) =>
        set((s) => ({ homeProfile: { ...s.homeProfile, ...fields } })),

      addAsset: (asset) =>
        set((s) => ({
          homeProfile: {
            ...s.homeProfile,
            assets: [
              ...s.homeProfile.assets,
              { ...asset, id: crypto.randomUUID() },
            ],
          },
        })),

      removeAsset: (id) =>
        set((s) => ({
          homeProfile: {
            ...s.homeProfile,
            assets: s.homeProfile.assets.filter((a) => a.id !== id),
          },
        })),

      addPaintColor: (paint) =>
        set((s) => ({
          homeProfile: {
            ...s.homeProfile,
            paintColors: [
              ...s.homeProfile.paintColors,
              { ...paint, id: crypto.randomUUID() },
            ],
          },
        })),

      removePaintColor: (id) =>
        set((s) => ({
          homeProfile: {
            ...s.homeProfile,
            paintColors: s.homeProfile.paintColors.filter((p) => p.id !== id),
          },
        })),

      addKeyEntry: (entry) =>
        set((s) => ({
          keyVault: [
            ...s.keyVault,
            { ...entry, id: crypto.randomUUID(), createdAt: new Date().toISOString() },
          ],
        })),

      removeKeyEntry: (id) =>
        set((s) => ({ keyVault: s.keyVault.filter((k) => k.id !== id) })),

      toggleKeyActive: (id) =>
        set((s) => ({
          keyVault: s.keyVault.map((k) =>
            k.id === id ? { ...k, isActive: !k.isActive } : k
          ),
        })),

      joinBlockParty: (partyId) =>
        set((s) => ({ joinedBlockParties: [...s.joinedBlockParties, partyId] })),
    }),
    { name: 'qs-customer-hub' }
  )
);
