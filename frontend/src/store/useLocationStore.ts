import { create } from 'zustand';

export type IntelligenceTier = 'NATIONAL' | 'REGIONAL' | 'DEEP';

export interface LocationState {
  // Geographic Hierarchy
  selectedCountry: string; // 'IN'
  selectedState: string | null; // 'IN-MH'
  selectedDistrict: string | null;
  selectedBasin: string | null; // 'BASIN-MITHI'
  selectedCity: string | null; // 'IN-MH-MUMBAI'
  selectedCatchment: string | null; // 'CATCH-MITHI-01'

  // Intelligence Tier & Operational Status
  activeIntelligenceLevel: IntelligenceTier;
  activeZoneId: string | null;
  displayName: string;
  mapCenter: [number, number];
  mapZoom: number;

  // Modal state
  isTierModalOpen: boolean;
  setTierModalOpen: (open: boolean) => void;

  // Actions
  setLocation: (update: Partial<LocationState>) => void;
  resetToMumbai: () => void;
  selectMahanadi: () => void;
  selectNational: () => void;
}

export const useLocationStore = create<LocationState>((set) => ({
  // Defaults to the foundational Mumbai Deep Intelligence Zone
  selectedCountry: 'IN',
  selectedState: 'IN-MH',
  selectedDistrict: null,
  selectedBasin: 'BASIN-MITHI',
  selectedCity: 'IN-MH-MUMBAI',
  selectedCatchment: 'CATCH-MITHI-01',
  activeIntelligenceLevel: 'DEEP',
  activeZoneId: 'deep_mumbai_mithi',
  displayName: 'Mumbai · Mithi Catchment',
  mapCenter: [19.076, 72.8777],
  mapZoom: 13,
  isTierModalOpen: false,

  setTierModalOpen: (open) => set({ isTierModalOpen: open }),

  setLocation: (update) => set((state) => ({ ...state, ...update })),

  resetToMumbai: () =>
    set({
      selectedCountry: 'IN',
      selectedState: 'IN-MH',
      selectedDistrict: null,
      selectedBasin: 'BASIN-MITHI',
      selectedCity: 'IN-MH-MUMBAI',
      selectedCatchment: 'CATCH-MITHI-01',
      activeIntelligenceLevel: 'DEEP',
      activeZoneId: 'deep_mumbai_mithi',
      displayName: 'Mumbai · Mithi Catchment',
      mapCenter: [19.076, 72.8777],
      mapZoom: 13,
    }),

  selectMahanadi: () =>
    set({
      selectedCountry: 'IN',
      selectedState: 'IN-OD',
      selectedDistrict: null,
      selectedBasin: 'BASIN-MAHANADI',
      selectedCity: null,
      selectedCatchment: null,
      activeIntelligenceLevel: 'REGIONAL',
      activeZoneId: 'regional_mahanadi_basin',
      displayName: 'Mahanadi Basin · Odisha (DFO 3382 Study)',
      mapCenter: [20.45, 85.85],
      mapZoom: 8,
    }),

  selectNational: () =>
    set({
      selectedCountry: 'IN',
      selectedState: null,
      selectedDistrict: null,
      selectedBasin: null,
      selectedCity: null,
      selectedCatchment: null,
      activeIntelligenceLevel: 'NATIONAL',
      activeZoneId: 'national_india',
      displayName: 'India (National Macro Screening)',
      mapCenter: [20.5937, 78.9629],
      mapZoom: 5,
    }),
}));
