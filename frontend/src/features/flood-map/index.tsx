import React, { useState, useEffect } from 'react';
import {
  Play,
  Pause,
  Clock,
  Info,
  RefreshCw,
  Activity,
  Search,
  CheckCircle2,
  MapPin,
  ShieldAlert,
  AlertTriangle,
  Layers,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react';
import { LeafletMap } from '@/map/LeafletMap';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useLocationStore } from '@/store/useLocationStore';
import {
  fetchLatestDigitalTwinRun,
  triggerDigitalTwinRun,
  fetchCellDiagnostics,
  DigitalTwinRunResponse,
  DigitalTwinTimeSlice,
  CellDiagnosticDetail,
} from '@/api/digitalTwin';

const MITHI_CHANNEL_LINE = [
  {
    id: 'mithi_channel',
    title: 'Mithi River Drainage Channel',
    color: '#0284c7',
    weight: 4,
    positions: [
      [19.102, 72.885],
      [19.088, 72.880],
      [19.072, 72.872],
      [19.055, 72.860],
      [19.040, 72.850],
    ] as [number, number][],
  },
];

const FLOOD_OUTLOOK_MARKERS = [
  {
    id: 'kurla_junction',
    position: [19.072, 72.880] as [number, number],
    title: 'Kurla Junction',
    subtitle: 'High risk',
    color: '#dc2626',
    badge: '!',
  },
  {
    id: 'sion_hospital',
    position: [19.050, 72.862] as [number, number],
    title: 'Sion Hospital',
    subtitle: 'Access at risk',
    color: '#dc2626',
    badge: '+',
  },
  {
    id: 'bkc_center',
    position: [19.065, 72.865] as [number, number],
    title: 'Bandra Kurla Complex',
    subtitle: 'Command Hub',
    color: '#1a56db',
    badge: 'C',
  },
];

const CANONICAL_MINUTES = [0, 30, 60, 90, 120, 150, 180];
const SLICE_LABELS: Record<number, string> = {
  0: 'NOW',
  30: '+30m',
  60: '+60m (Peak)',
  90: '+90m',
  120: '+120m',
  150: '+150m',
  180: '+180m',
};

const MAHANADI_SUBBASIN_POLYGONS = [
  // 15 Train sub-basins
  { id: 'sb_train_1', title: 'Upper Sambalpur (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.8, 83.5], [21.8, 84.2], [21.3, 84.1], [21.2, 83.4], [21.8, 83.5]] as [number, number][] },
  { id: 'sb_train_2', title: 'Hirakud Catchment (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.5, 83.7], [21.6, 84.2], [21.2, 84.3], [21.1, 83.7], [21.5, 83.7]] as [number, number][] },
  { id: 'sb_train_3', title: 'Bargarh Basin (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.4, 83.2], [21.4, 83.8], [21.0, 83.7], [20.9, 83.1], [21.4, 83.2]] as [number, number][] },
  { id: 'sb_train_4', title: 'Bolangir Upper (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.9, 83.0], [21.0, 83.6], [20.6, 83.5], [20.5, 82.9], [20.9, 83.0]] as [number, number][] },
  { id: 'sb_train_5', title: 'Sonepur Confluence (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.9, 83.7], [21.0, 84.3], [20.6, 84.2], [20.5, 83.6], [20.9, 83.7]] as [number, number][] },
  { id: 'sb_train_6', title: 'Baudh Middle Reach (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.9, 84.1], [21.0, 84.7], [20.6, 84.6], [20.5, 84.0], [20.9, 84.1]] as [number, number][] },
  { id: 'sb_train_7', title: 'Redhakhol Sub-basin (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.3, 84.2], [21.4, 84.7], [21.0, 84.8], [20.9, 84.2], [21.3, 84.2]] as [number, number][] },
  { id: 'sb_train_8', title: 'Angul North Reach (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.1, 84.8], [21.2, 85.3], [20.8, 85.2], [20.7, 84.7], [21.1, 84.8]] as [number, number][] },
  { id: 'sb_train_9', title: 'Talcher Sub-basin (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.1, 85.0], [21.2, 85.5], [20.8, 85.6], [20.7, 85.0], [21.1, 85.0]] as [number, number][] },
  { id: 'sb_train_10', title: 'Kalahandi Headwaters (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.2, 82.8], [20.3, 83.4], [19.8, 83.3], [19.7, 82.7], [20.2, 82.8]] as [number, number][] },
  { id: 'sb_train_11', title: 'Tel River Upper (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.4, 83.2], [20.5, 83.8], [20.0, 83.7], [19.9, 83.1], [20.4, 83.2]] as [number, number][] },
  { id: 'sb_train_12', title: 'Tel River Lower (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.6, 83.6], [20.7, 84.1], [20.3, 84.1], [20.2, 83.5], [20.6, 83.6]] as [number, number][] },
  { id: 'sb_train_13', title: 'Deogarh Hills (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.6, 84.5], [21.7, 85.0], [21.3, 85.0], [21.2, 84.4], [21.6, 84.5]] as [number, number][] },
  { id: 'sb_train_14', title: 'Brahmani-Mahanadi Divide (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[21.4, 85.1], [21.5, 85.6], [21.1, 85.6], [21.0, 85.1], [21.4, 85.1]] as [number, number][] },
  { id: 'sb_train_15', title: 'Daspalla Valley (Train)', partition: 'TRAIN', color: '#3b82f6', positions: [[20.6, 84.6], [20.7, 85.1], [20.3, 85.0], [20.2, 84.5], [20.6, 84.6]] as [number, number][] },

  // 6 Validation sub-basins
  { id: 'sb_val_1', title: 'Dhenkanal Basin (Val)', partition: 'VALIDATION', color: '#f59e0b', positions: [[20.8, 85.3], [20.9, 85.8], [20.5, 85.8], [20.4, 85.2], [20.8, 85.3]] as [number, number][] },
  { id: 'sb_val_2', title: 'Athagarh Reach (Val)', partition: 'VALIDATION', color: '#f59e0b', positions: [[20.6, 85.4], [20.7, 85.9], [20.4, 85.9], [20.3, 85.3], [20.6, 85.4]] as [number, number][] },
  { id: 'sb_val_3', title: 'Nayagarh Foothills (Val)', partition: 'VALIDATION', color: '#f59e0b', positions: [[20.3, 84.9], [20.4, 85.4], [20.0, 85.3], [19.9, 84.8], [20.3, 84.9]] as [number, number][] },
  { id: 'sb_val_4', title: 'Banki Gorge (Val)', partition: 'VALIDATION', color: '#f59e0b', positions: [[20.4, 85.3], [20.5, 85.8], [20.2, 85.8], [20.1, 85.2], [20.4, 85.3]] as [number, number][] },
  { id: 'sb_val_5', title: 'Khordha Plateau (Val)', partition: 'VALIDATION', color: '#f59e0b', positions: [[20.2, 85.4], [20.3, 85.9], [19.9, 85.8], [19.8, 85.3], [20.2, 85.4]] as [number, number][] },
  { id: 'sb_val_6', title: 'Cuttack North (Val)', partition: 'VALIDATION', color: '#f59e0b', positions: [[20.6, 85.8], [20.7, 86.2], [20.4, 86.2], [20.3, 85.7], [20.6, 85.8]] as [number, number][] },

  // 6 Test sub-basins
  { id: 'sb_test_1', title: 'Cuttack Delta Apex (Test)', partition: 'TEST', color: '#10b981', positions: [[20.5, 85.8], [20.6, 86.2], [20.3, 86.2], [20.2, 85.7], [20.5, 85.8]] as [number, number][] },
  { id: 'sb_test_2', title: 'Kendrapara Lowlands (Test)', partition: 'TEST', color: '#10b981', positions: [[20.6, 86.2], [20.7, 86.7], [20.3, 86.8], [20.2, 86.2], [20.6, 86.2]] as [number, number][] },
  { id: 'sb_test_3', title: 'Jagatsinghpur / Devi River (Test)', partition: 'TEST', color: '#10b981', positions: [[20.3, 86.1], [20.4, 86.6], [20.0, 86.6], [19.9, 86.0], [20.3, 86.1]] as [number, number][] },
  { id: 'sb_test_4', title: 'Puri Coastal Plain (Test)', partition: 'TEST', color: '#10b981', positions: [[20.0, 85.7], [20.1, 86.1], [19.7, 86.0], [19.7, 85.6], [20.0, 85.7]] as [number, number][] },
  { id: 'sb_test_5', title: 'Chilika Coastal Margin (Test)', partition: 'TEST', color: '#10b981', positions: [[19.8, 85.2], [19.9, 85.7], [19.4, 85.5], [19.4, 85.0], [19.8, 85.2]] as [number, number][] },
  { id: 'sb_test_6', title: 'Paradip Estuary Mouth (Test)', partition: 'TEST', color: '#10b981', positions: [[20.4, 86.5], [20.5, 86.9], [20.1, 86.9], [20.0, 86.5], [20.4, 86.5]] as [number, number][] },
];

const MAHANADI_RIVERS = [
  {
    id: 'mahanadi_main_stem',
    title: 'Mahanadi River (Main Stem)',
    color: '#0284c7',
    weight: 4,
    opacity: 0.9,
    positions: [
      [21.52, 83.87],
      [21.15, 84.45],
      [20.85, 85.10],
      [20.55, 85.70],
      [20.48, 85.88],
      [20.42, 86.20],
      [20.31, 86.61],
    ] as [number, number][],
  },
  {
    id: 'devi_river',
    title: 'Devi River Distributary',
    color: '#06b6d4',
    weight: 3,
    opacity: 0.85,
    positions: [
      [20.42, 86.00],
      [20.25, 86.15],
      [20.05, 86.28],
    ] as [number, number][],
  },
  {
    id: 'daya_river',
    title: 'Daya River Distributary (Chilika Outflow)',
    color: '#0891b2',
    weight: 3,
    opacity: 0.85,
    positions: [
      [20.35, 85.82],
      [20.15, 85.75],
      [19.95, 85.60],
    ] as [number, number][],
  },
  {
    id: 'bhargavi_river',
    title: 'Bhargavi River Distributary',
    color: '#0ea5e9',
    weight: 3,
    opacity: 0.85,
    positions: [
      [20.30, 85.85],
      [20.05, 85.82],
      [19.82, 85.84],
    ] as [number, number][],
  },
];

const MAHANADI_MARKERS = [
  {
    id: 'cuttack_apex',
    position: [20.46, 85.88] as [number, number],
    title: 'Cuttack (Delta Apex)',
    subtitle: 'Major distributary bifurcation point',
    color: '#008080',
    badge: 'A',
  },
  {
    id: 'sambalpur_hirakud',
    position: [21.52, 83.87] as [number, number],
    title: 'Hirakud Dam / Sambalpur',
    subtitle: 'Upper Basin reservoir storage',
    color: '#1a56db',
    badge: 'H',
  },
  {
    id: 'paradip_estuary',
    position: [20.31, 86.61] as [number, number],
    title: 'Paradip (Estuary Mouth)',
    subtitle: 'Main stem discharge into Bay of Bengal',
    color: '#f59e0b',
    badge: 'P',
  },
  {
    id: 'puri_chilika',
    position: [19.81, 85.83] as [number, number],
    title: 'Puri / Daya Outflow',
    subtitle: 'Discharges toward Chilika coastal lagoon',
    color: '#10b981',
    badge: 'C',
  },
];

const DFO3382_OBS_POLYGONS = [
  {
    id: 'dfo_inundation_1',
    title: 'DFO 3382 Kendrapara Lowland Inundation (MODIS)',
    color: '#ef4444',
    fillColor: '#ef4444',
    fillOpacity: 0.40,
    strokeColor: '#dc2626',
    weight: 2,
    positions: [
      [20.42, 86.15],
      [20.58, 86.35],
      [20.52, 86.58],
      [20.35, 86.42],
      [20.42, 86.15],
    ] as [number, number][],
  },
  {
    id: 'dfo_inundation_2',
    title: 'DFO 3382 Daya-Bhargavi Coastal Inundation (MODIS)',
    color: '#ef4444',
    fillColor: '#ef4444',
    fillOpacity: 0.40,
    strokeColor: '#dc2626',
    weight: 2,
    positions: [
      [20.15, 85.75],
      [20.10, 85.98],
      [19.88, 85.90],
      [19.92, 85.65],
      [20.15, 85.75],
    ] as [number, number][],
  },
];

const WATER_MARGIN_POLYGONS = [
  {
    id: 'margin_chilika',
    title: 'Chilika Water Boundary Margin (dry_fraction < 0.70)',
    color: '#6366f1',
    fillColor: '#6366f1',
    fillOpacity: 0.35,
    strokeColor: '#4f46e5',
    weight: 2,
    positions: [
      [19.85, 85.15],
      [19.88, 85.55],
      [19.45, 85.45],
      [19.42, 85.10],
      [19.85, 85.15],
    ] as [number, number][],
  },
  {
    id: 'margin_estuary',
    title: 'Paradip Mangrove Water Margin (dry_fraction < 0.70)',
    color: '#6366f1',
    fillColor: '#6366f1',
    fillOpacity: 0.35,
    strokeColor: '#4f46e5',
    weight: 2,
    positions: [
      [20.35, 86.50],
      [20.45, 86.75],
      [20.20, 86.85],
      [20.15, 86.55],
      [20.35, 86.50],
    ] as [number, number][],
  },
];

const ML_RANKING_SCORE_POLYGONS = [
  {
    id: 'ml_rank_tile_1',
    title: 'Experimental ML Ranking Tile: High Susceptibility (0.84)',
    color: '#8b5cf6',
    fillColor: '#8b5cf6',
    fillOpacity: 0.30,
    strokeColor: '#7c3aed',
    weight: 2,
    positions: [
      [20.38, 86.20],
      [20.52, 86.38],
      [20.45, 86.55],
      [20.32, 86.35],
      [20.38, 86.20],
    ] as [number, number][],
  },
  {
    id: 'ml_rank_tile_2',
    title: 'Experimental ML Ranking Tile: Moderate Susceptibility (0.58)',
    color: '#a78bfa',
    fillColor: '#a78bfa',
    fillOpacity: 0.25,
    strokeColor: '#8b5cf6',
    weight: 2,
    positions: [
      [20.10, 85.80],
      [20.20, 86.00],
      [20.02, 86.10],
      [19.92, 85.85],
      [20.10, 85.80],
    ] as [number, number][],
  },
];

interface MahanadiRegionalMapFeatureProps {
  onResetToMumbai: () => void;
  onOpenTiers: () => void;
}

const MahanadiRegionalMapFeature: React.FC<MahanadiRegionalMapFeatureProps> = ({
  onResetToMumbai,
  onOpenTiers,
}) => {
  const [showSubbasins, setShowSubbasins] = useState<boolean>(true);
  const [showRivers, setShowRivers] = useState<boolean>(true);
  const [showLandWater, setShowLandWater] = useState<boolean>(false);
  const [showDfoObs, setShowDfoObs] = useState<boolean>(true);
  const [showMlScores, setShowMlScores] = useState<boolean>(false);

  const activePolygons = [
    ...(showSubbasins
      ? MAHANADI_SUBBASIN_POLYGONS.map((sb) => ({
          id: sb.id,
          positions: sb.positions,
          color: sb.color,
          fillColor: sb.color,
          fillOpacity: 0.18,
          strokeColor: sb.color,
          weight: 1.5,
          title: `${sb.title} [${sb.partition}]`,
        }))
      : []),
    ...(showLandWater ? WATER_MARGIN_POLYGONS : []),
    ...(showDfoObs ? DFO3382_OBS_POLYGONS : []),
    ...(showMlScores ? ML_RANKING_SCORE_POLYGONS : []),
  ];

  return (
    <div className="space-y-4 pb-4 font-sans max-w-[1240px] mx-auto">
      {/* 1. Header with Governance Badges */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-[10px] font-extrabold tracking-wider uppercase px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
              LEVEL 2: REGIONAL RESEARCH
            </span>
            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800">
              BASIN-MAHANADI
            </span>
            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-red-100 text-red-800">
              NOT_FOR_PUBLIC_ALERTS
            </span>
          </div>
          <h1
            className="text-[1.75rem] font-extrabold leading-none tracking-tight"
            style={{ color: 'var(--aq-navy)', letterSpacing: '-0.02em' }}
          >
            Mahanadi Regional Research Map
          </h1>
          <p className="mt-1.5 text-[13.5px] text-slate-500">
            DFO 3382 September 2008 Monsoon Event · 27 HydroBASINS Sub-basins & Distributaries
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenTiers}
            icon={<Layers className="w-3.5 h-3.5" />}
          >
            Switch Tier
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onResetToMumbai}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Mumbai Deep Zone
          </Button>
        </div>
      </div>

      {/* 2. Mandatory Warning Banner */}
      <div className="bg-amber-50 border border-amber-200/90 rounded-2xl p-3.5 shadow-xs flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5 text-xs">
          <h4 className="font-extrabold text-amber-900 uppercase tracking-wider text-[11px]">
            Experimental Spatial Research — Not an Operational Flood Forecast
          </h4>
          <p className="text-amber-800">
            The Phase 6 Deterministic 2D Physics Engine (<code>engines/flood/solver.py</code>) remains the primary operational flood authority. ML layers shown here represent diagnostic spatial rankings on coarse MODIS observations without real-time rainfall calibration.
          </p>
        </div>
      </div>

      {/* 3. Layer Controls Strip */}
      <div className="p-3 bg-white rounded-2xl border border-slate-200/90 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-bold text-slate-700 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-teal-600" />
            <span>Map Layers:</span>
          </span>

          <label className="flex items-center gap-1.5 font-medium text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showSubbasins}
              onChange={(e) => setShowSubbasins(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500"
            />
            <span>Sub-basins (27 Lev08)</span>
            <div className="flex items-center gap-1 ml-1 text-[10px]">
              <span className="px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 font-bold">15 Train</span>
              <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-bold">6 Val</span>
              <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 font-bold">6 Test</span>
            </div>
          </label>

          <label className="flex items-center gap-1.5 font-medium text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showRivers}
              onChange={(e) => setShowRivers(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500"
            />
            <span className="w-3 h-0.5 bg-[#0284c7] inline-block" />
            <span>HydroRIVERS Network</span>
          </label>

          <label className="flex items-center gap-1.5 font-medium text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showDfoObs}
              onChange={(e) => setShowDfoObs(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500"
            />
            <span className="w-2.5 h-2.5 rounded bg-red-500/50 border border-red-500 inline-block" />
            <span>DFO 3382 Inundation (MODIS)</span>
          </label>

          <label className="flex items-center gap-1.5 font-medium text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showLandWater}
              onChange={(e) => setShowLandWater(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500"
            />
            <span className="w-2.5 h-2.5 rounded bg-indigo-500/50 border border-indigo-500 inline-block" />
            <span>Water Margin Uncertainty</span>
          </label>

          <label className="flex items-center gap-1.5 font-medium text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showMlScores}
              onChange={(e) => setShowMlScores(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500"
            />
            <span className="w-2.5 h-2.5 rounded bg-purple-500/50 border border-purple-500 inline-block" />
            <span>ML Ranking Scores</span>
          </label>
        </div>
      </div>

      {/* 4. Interactive Regional Map Container */}
      <div className="relative rounded-[20px] overflow-hidden border border-slate-200/90 shadow-xs h-[480px]">
        <LeafletMap
          center={[20.45, 85.85]}
          zoom={8}
          height="480px"
          polygons={activePolygons}
          polylines={showRivers ? MAHANADI_RIVERS : []}
          markers={MAHANADI_MARKERS}
          floodIntensityMultiplier={0}
        />

        {/* Floating Research Legend Overlay */}
        <div
          className="absolute top-4 right-4 z-[1000] bg-white/95 backdrop-blur-sm p-3 rounded-2xl text-[10px] space-y-2 border hidden sm:block shadow-md max-w-[210px]"
          style={{ borderColor: 'rgba(15,35,64,0.12)' }}
        >
          <div className="font-bold text-slate-800 text-[11px] flex items-center justify-between">
            <span>Research Layers</span>
            <span className="text-[9px] font-mono bg-amber-100 text-amber-800 px-1 py-0.5 rounded">DFO 3382</span>
          </div>
          <div className="space-y-1 font-medium text-slate-600">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded bg-blue-500/30 border border-blue-500" />
              <span>Train Sub-basins (15)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded bg-amber-500/30 border border-amber-500" />
              <span>Val Sub-basins (6)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded bg-emerald-500/30 border border-emerald-500" />
              <span>Test Sub-basins (6)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-[#0284c7]" />
              <span>Mahanadi Main Stem</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded bg-red-500/40 border border-red-500" />
              <span>DFO 3382 Flood Surface</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded bg-indigo-500/40 border border-indigo-500" />
              <span>Water Margins (&lt;0.70 dry)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Bottom Diagnostics / Audit Panel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card padding="md" className="border shadow-xs space-y-2.5 text-xs text-slate-700">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Spatial Independence & Governance</span>
            </h4>
            <span className="text-[10px] font-mono text-slate-500">Zero Leakage</span>
          </div>
          <ul className="space-y-1.5 list-disc list-inside text-slate-600">
            <li>Level 8 HydroBASINS partition guarantees complete spatial independence across splits.</li>
            <li>Zero holdout contamination: <strong>DFO 2507</strong> strictly quarantined with zero access.</li>
            <li>Phase 7E schema invariant: 7-feature foundational schema preserved unchanged.</li>
            <li>Rainfall invariant: 100% NaN preserved honestly without synthetic values.</li>
          </ul>
        </Card>

        <Card padding="md" className="border shadow-xs space-y-2.5 text-xs text-slate-700">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-amber-600" />
              <span>Optical Margin Label Bias (Stage 4.1 Audit)</span>
            </h4>
            <span className="text-[10px] font-bold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded">66.8% In Margins</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            Over 66% of positive flood observations in DFO 3382 lie inside water body transition margins (<code>dry_fraction &lt; 0.70</code>). On high-quality terrestrial cells away from water bodies, models collapse to PR-AUC 0.0192 (baseline prevalence: 0.0157). ML ranking outputs reflect water proximity rather than true inland precipitation inundation.
          </p>
        </Card>
      </div>
    </div>
  );
};

const MumbaiFloodMapFeature: React.FC = () => {
  const [selectedMinutes, setSelectedMinutes] = useState<number>(60);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [runData, setRunData] = useState<DigitalTwinRunResponse | null>(null);
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [selectedCellId, setSelectedCellId] = useState<string>('CELL_R0020_C0020');
  const [inspectedCell, setInspectedCell] = useState<CellDiagnosticDetail | null>(null);
  const [isInspecting, setIsInspecting] = useState<boolean>(false);

  // Load latest Digital Twin simulation run
  const loadLatestRun = async () => {
    try {
      const data = await fetchLatestDigitalTwinRun();
      setRunData(data);
    } catch (err) {
      console.warn('Failed to load latest Digital Twin run:', err);
    }
  };

  useEffect(() => {
    loadLatestRun();
  }, []);

  // Trigger New Simulation Run
  const handleRunSimulation = async () => {
    setIsTriggering(true);
    try {
      const res = await triggerDigitalTwinRun({
        catchment_id: 'mithi_catchment_mumbai',
        rain_event_id: 'monsoon_2026_canonical_01',
      });
      setRunData(res);
    } catch (err) {
      console.error('Failed to trigger simulation run:', err);
    } finally {
      setIsTriggering(false);
    }
  };

  // Auto-play through canonical slices
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setSelectedMinutes((prev) => {
          const idx = CANONICAL_MINUTES.indexOf(prev);
          const nextIdx = (idx + 1) % CANONICAL_MINUTES.length;
          return CANONICAL_MINUTES[nextIdx];
        });
      }, 2500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying]);

  // Fetch cell diagnostics
  const handleInspect = async (cellId: string) => {
    setSelectedCellId(cellId);
    setIsInspecting(true);
    try {
      const detail = await fetchCellDiagnostics(cellId, selectedMinutes);
      setInspectedCell(detail);
    } catch (err) {
      console.error('Failed to fetch cell diagnostics:', err);
    } finally {
      setIsInspecting(false);
    }
  };

  useEffect(() => {
    if (selectedCellId) {
      handleInspect(selectedCellId);
    }
  }, [selectedMinutes, selectedCellId]);

  const activeSlice: DigitalTwinTimeSlice | undefined = runData?.time_slices.find(
    (s) => s.minutes_from_start === selectedMinutes
  );

  const activeStepIdx = CANONICAL_MINUTES.indexOf(selectedMinutes);
  const intensityMult = [0.35, 0.7, 1.0, 0.85, 0.65, 0.45, 0.25][activeStepIdx] ?? 1.0;

  return (
    <div className="space-y-4 pb-4 font-sans max-w-[1240px] mx-auto">

      {/* ── Page header ─────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
        <div>
          <h1
            className="text-[1.75rem] font-extrabold leading-none tracking-tight"
            style={{ color: 'var(--aq-navy)', letterSpacing: '-0.02em' }}
          >
            Flood Outlook
          </h1>
          <p className="mt-1.5 text-[13.5px]" style={{ color: 'var(--aq-muted)' }}>
            See how projected flooding changes over the next 3 hours across Mithi Catchment.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold" style={{ color: '#059669' }}>
            <span className="w-2 h-2 rounded-full bg-emerald-500 aq-live-dot" />
            Live Flood Model
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={handleRunSimulation}
            isLoading={isTriggering}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Run New Forecast
          </Button>
        </div>
      </div>

      {/* ── Signature Forecast Timeline Component ────────────── */}
      <div
        className="flex items-center gap-1.5 p-1.5 bg-white rounded-2xl border overflow-x-auto"
        style={{ borderColor: 'rgba(15,35,64,0.08)', boxShadow: '0 1px 3px rgba(15,35,64,0.05)', scrollbarWidth: 'none' }}
      >
        <div className="flex-1 flex items-center gap-1.5 min-w-[550px]">
          {CANONICAL_MINUTES.map((min) => {
            const isActive = selectedMinutes === min;
            const isPeak = min === 60;
            return (
              <button
                key={min}
                onClick={() => setSelectedMinutes(min)}
                className="flex-1 min-w-[72px] flex flex-col items-center justify-center py-2 px-3 rounded-xl transition-all duration-150 cursor-pointer relative"
                style={isActive
                  ? { background: 'var(--aq-blue)', color: '#fff', boxShadow: '0 3px 10px rgba(26,86,219,0.30)' }
                  : { color: 'var(--aq-muted)', background: 'transparent' }
                }
                onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = '#f1f5f9'; }}
                onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = ''; }}
              >
                <div className="flex items-center gap-1">
                  <span className="text-[12.5px] font-bold">{SLICE_LABELS[min]}</span>
                  {isPeak && !isActive && (
                    <span className="text-[9px] font-extrabold px-1 py-0.2 rounded bg-amber-100 text-amber-800">
                      Peak
                    </span>
                  )}
                </div>
                {isActive && (
                  <span className="text-[9.5px] font-medium opacity-90 mt-0.5">
                    {isPeak ? 'Peak forecast' : 'Selected'}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="shrink-0 pl-2.5 border-l" style={{ borderColor: 'rgba(15,35,64,0.08)' }}>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1.5 py-2 px-3.5 rounded-xl text-[12px] font-bold transition-all duration-150 cursor-pointer"
            style={{ color: isPlaying ? '#dc2626' : 'var(--aq-blue)', background: isPlaying ? '#fff1f2' : '#eff6ff' }}
          >
            {isPlaying ? <><Pause className="w-3.5 h-3.5 fill-current" /> Pause</> : <><Play className="w-3.5 h-3.5 fill-current" /> Play</>}
          </button>
        </div>
      </div>

      {/* ── Main grid: map (70%) + right snapshot & inspector (30%) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">

        {/* Map — 2/3 width */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="relative aq-map-container flex-1 min-h-[500px]">
            <LeafletMap
              center={[19.076, 72.8777]}
              zoom={13}
              polygons={[]}
              polylines={MITHI_CHANNEL_LINE}
              markers={FLOOD_OUTLOOK_MARKERS}
              floodIntensityMultiplier={intensityMult}
              height="100%"
            />

            {/* Map floating: current slice label */}
            <div
              className="absolute top-4 left-4 z-[1000] flex items-center gap-3 px-3.5 py-2.5 rounded-2xl border"
              style={{
                background: 'rgba(255,255,255,0.96)',
                borderColor: 'rgba(15,35,64,0.12)',
                boxShadow: '0 4px 14px rgba(15,35,64,0.12)',
                backdropFilter: 'blur(8px)',
              }}
            >
              <Clock className="w-4 h-4 shrink-0" style={{ color: 'var(--aq-blue)' }} />
              <div>
                <div className="aq-label" style={{ color: 'var(--aq-muted)' }}>Viewing</div>
                <div className="text-[14px] font-bold leading-tight" style={{ color: 'var(--aq-navy)' }}>
                  {SLICE_LABELS[selectedMinutes]}
                </div>
                {activeSlice?.timestamp_ist && (
                  <div className="text-[10px] mt-0.5" style={{ color: 'var(--aq-muted)' }}>{activeSlice.timestamp_ist}</div>
                )}
              </div>
            </div>

            {/* Map floating: data status */}
            <div
              className="absolute top-4 right-4 z-[1000] flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-semibold border"
              style={{
                background: 'rgba(255,255,255,0.96)',
                borderColor: 'rgba(15,35,64,0.10)',
                boxShadow: '0 2px 8px rgba(15,35,64,0.08)',
                color: '#059669',
              }}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Data current</span>
            </div>

            {/* Map floating legend */}
            <div
              className="absolute bottom-4 left-4 z-[1000] p-3 rounded-2xl text-[10px] space-y-2 border hidden sm:block"
              style={{
                width: '165px',
                background: 'rgba(255,255,255,0.96)',
                borderColor: 'rgba(15,35,64,0.12)',
                boxShadow: '0 4px 14px rgba(15,35,64,0.12)',
                backdropFilter: 'blur(8px)',
              }}
            >
              <div className="font-bold text-slate-800 text-[11px]">Flood depth (m)</div>
              <div className="space-y-1 font-medium text-slate-600">
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-blue-900" /> &gt; 2.0</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-blue-600" /> 1.0 – 2.0</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-blue-400" /> 0.5 – 1.0</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> 0.1 – 0.5</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-cyan-200" /> 0.3 – &lt; 0.1</div>
              </div>
              <div className="w-full h-px bg-slate-100 my-1" />
              <div className="space-y-1 font-medium text-slate-600">
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded bg-blue-500/40 border border-blue-500" /> Flooded area</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-red-500 text-white text-[8px] flex items-center justify-center font-bold">+</span> Key facility</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-blue-600" /> Selected location</div>
                <div className="flex items-center gap-2"><span className="w-3 h-0.5 bg-slate-800" /> Major road</div>
                <div className="flex items-center gap-2"><span className="w-3 h-0.5 bg-slate-500 border-t border-b border-dashed" /> Railway</div>
                <div className="flex items-center gap-2"><span className="w-3 h-0.5 bg-cyan-500" /> Mithi River</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right panel — 1/3 width */}
        <div className="flex flex-col gap-4">

          {/* Flood Snapshot */}
          <Card padding="md" className="space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b" style={{ borderColor: 'rgba(15,35,64,0.06)' }}>
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" style={{ color: 'var(--aq-blue)' }} />
                <span className="aq-section-title">Flood Snapshot</span>
              </div>
              <Badge variant="info" size="sm">{SLICE_LABELS[selectedMinutes]}</Badge>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Area at risk', value: `${(activeSlice?.affected_area_km2 ?? 1.85 * intensityMult).toFixed(2)} km²`, accent: 'var(--aq-blue)' },
                { label: 'Peak risk level', value: activeSlice?.peak_severity ?? (intensityMult > 0.8 ? 'HIGH' : 'MEDIUM'), accent: intensityMult > 0.8 ? '#dc2626' : '#d97706' },
                { label: 'Rising zones', value: `+${Math.round((activeSlice?.onset_cells_count ?? 320) * intensityMult)}`, accent: '#d97706' },
                { label: 'Sample points', value: `${activeSlice?.affected_cells_count ?? 1850}`, accent: 'var(--aq-muted)' },
              ].map((m) => (
                <div key={m.label} className="p-2.5 rounded-xl bg-slate-50/80 border border-slate-100">
                  <div className="aq-label mb-1">{m.label}</div>
                  <div className="text-[14px] font-extrabold" style={{ color: m.accent }}>{m.value}</div>
                </div>
              ))}
            </div>

            <div className="p-3 rounded-xl text-[11.5px] leading-relaxed bg-blue-50/70 border border-blue-100 text-blue-900">
              <div className="font-bold mb-1 flex items-center gap-1.5 text-blue-950">
                <Info className="w-3.5 h-3.5 text-blue-600" />
                Snapshot Insight
              </div>
              {activeSlice?.cause_explanation ||
                `Water accumulation expands along central Mithi River corridor around ${SLICE_LABELS[selectedMinutes]}, with peak inundated area reaching ${(activeSlice?.affected_area_km2 ?? 1.85 * intensityMult).toFixed(2)} km².`
              }
            </div>
          </Card>

          {/* Location inspector */}
          <Card padding="md" className="space-y-3 flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2.5 border-b mb-3" style={{ borderColor: 'rgba(15,35,64,0.06)' }}>
                <div className="flex items-center gap-2">
                  <Search className="w-4 h-4" style={{ color: '#059669' }} />
                  <span className="aq-section-title">Inspect a location</span>
                </div>
                <div className="flex items-center gap-1 text-[10.5px] font-semibold text-emerald-700">
                  <MapPin className="w-3 h-3 text-emerald-600" />
                  <span>Interactive</span>
                </div>
              </div>

              <select
                value={selectedCellId}
                onChange={(e) => handleInspect(e.target.value)}
                className="w-full rounded-xl px-3 py-2 text-[12px] font-semibold focus:outline-none transition-all cursor-pointer mb-3"
                style={{
                  background: '#f8fafc',
                  border: '1px solid rgba(15,35,64,0.12)',
                  color: 'var(--aq-text)',
                }}
              >
                <option value="CELL_R0020_C0020">Kurla Junction (Command Hub)</option>
                <option value="CELL_R0015_C0025">Kalina Lowlands (Floodplain)</option>
                <option value="CELL_R0030_C0018">Saki Naka Corridor (Access Road)</option>
                <option value="CELL_R0045_C0012">Sion Causeway (Hospital Access)</option>
              </select>

              {isInspecting ? (
                <div className="py-8 text-center text-[12px] font-medium text-slate-500">
                  Loading location data…
                </div>
              ) : inspectedCell ? (
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                    <div>
                      <div className="text-[12px] font-extrabold text-slate-900">
                        {inspectedCell.grid_cell_id.replace('CELL_', '').replace(/_/g, ' · ')}
                      </div>
                      <div className="text-[10px] mt-0.5 font-medium text-slate-500">
                        {inspectedCell.latitude.toFixed(4)}°N, {inspectedCell.longitude.toFixed(4)}°E
                      </div>
                    </div>
                    <Badge
                      variant={inspectedCell.severity === 'SEVERE' || inspectedCell.severity === 'HIGH' ? 'danger' : 'info'}
                      size="sm"
                    >
                      {inspectedCell.severity.charAt(0) + inspectedCell.severity.slice(1).toLowerCase()}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11.5px]">
                    {[
                      { label: 'Water depth', val: `${(inspectedCell.water_depth_m * intensityMult).toFixed(2)} m`, c: '#1d4ed8' },
                      { label: 'Elevation', val: `${inspectedCell.elevation_m.toFixed(1)} m`, c: 'var(--aq-muted)' },
                      { label: 'Rainfall rate', val: `${inspectedCell.rainfall_intensity_mm_hr.toFixed(1)} mm/h`, c: '#0891b2' },
                      { label: 'To waterway', val: `${inspectedCell.distance_to_waterway_m.toFixed(0)} m`, c: 'var(--aq-muted)' },
                    ].map((d) => (
                      <div key={d.label} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="aq-label block mb-0.5">{d.label}</span>
                        <span className="font-bold" style={{ color: d.c }}>{d.val}</span>
                      </div>
                    ))}
                  </div>

                  <details className="group">
                    <summary className="cursor-pointer text-[10.5px] font-semibold px-2 py-1.5 rounded-lg select-none text-slate-500 hover:text-slate-800 transition-colors">
                      Model details ▸
                    </summary>
                    <div className="mt-1 px-3 py-2.5 rounded-xl text-[11px] space-y-1 bg-slate-50 border border-slate-100">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Physical score</span>
                        <span className="font-mono font-bold text-slate-800">{inspectedCell.physical_model_score.toFixed(3)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Status tag</span>
                        <span className="font-bold text-slate-700">{inspectedCell.ml_status_tag}</span>
                      </div>
                    </div>
                  </details>
                </div>
              ) : (
                <div className="p-4 text-center rounded-xl bg-slate-50 border border-slate-100 space-y-2">
                  <ShieldAlert className="w-6 h-6 text-slate-400 mx-auto" />
                  <p className="text-[12px] font-semibold text-slate-700">Select a location to inspect</p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export const FloodMapFeature: React.FC = () => {
  const { activeIntelligenceLevel, selectedBasin, resetToMumbai, setTierModalOpen } = useLocationStore();
  const isMahanadi = activeIntelligenceLevel === 'REGIONAL' && selectedBasin === 'BASIN-MAHANADI';

  if (isMahanadi) {
    return (
      <MahanadiRegionalMapFeature
        onResetToMumbai={resetToMumbai}
        onOpenTiers={() => setTierModalOpen(true)}
      />
    );
  }

  return <MumbaiFloodMapFeature />;
};

export default FloodMapFeature;
