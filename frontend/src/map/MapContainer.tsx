import React from 'react';
import { LeafletMap } from './LeafletMap';
import { useLocationStore } from '@/store/useLocationStore';

export const MapContainer: React.FC<{
  center?: [number, number];
  zoom?: number;
  className?: string;
  height?: string;
  floodIntensityMultiplier?: number;
}> = ({ center, zoom, className, height = '400px', floodIntensityMultiplier = 1.0 }) => {
  const storeCenter = useLocationStore((s) => s.mapCenter);
  const storeZoom = useLocationStore((s) => s.mapZoom);
  const effectiveCenter = center || storeCenter;
  const effectiveZoom = zoom !== undefined ? zoom : storeZoom;

  const activeIntelligenceLevel = useLocationStore((s) => s.activeIntelligenceLevel);
  const selectedBasin = useLocationStore((s) => s.selectedBasin);

  const isMahanadi = activeIntelligenceLevel === 'REGIONAL' && selectedBasin === 'BASIN-MAHANADI';

  const polylines = isMahanadi
    ? [
        {
          id: 'mahanadi_main_stem',
          title: 'Mahanadi Main Stem',
          positions: [
            [20.55, 85.70],
            [20.48, 85.88],
            [20.42, 86.20],
            [20.31, 86.61],
          ] as [number, number][],
          color: '#0284c7',
          weight: 4,
          opacity: 0.9,
        },
        {
          id: 'devi_distributary',
          title: 'Devi River Branch',
          positions: [
            [20.42, 86.00],
            [20.25, 86.15],
            [20.05, 86.28],
          ] as [number, number][],
          color: '#06b6d4',
          weight: 3,
          opacity: 0.85,
        },
        {
          id: 'daya_distributary',
          title: 'Daya River Branch',
          positions: [
            [20.35, 85.82],
            [20.15, 85.75],
            [19.95, 85.60],
          ] as [number, number][],
          color: '#0891b2',
          weight: 3,
          opacity: 0.85,
        },
      ]
    : [
        {
          id: 'mithi_river_main',
          title: 'Mithi River Corridor',
          positions: [
            [19.120, 72.895],
            [19.102, 72.885],
            [19.088, 72.880],
            [19.072, 72.872],
            [19.055, 72.860],
            [19.040, 72.850],
          ] as [number, number][],
          color: '#0284c7',
          weight: 4,
          opacity: 0.9,
        },
      ];

  const markers = isMahanadi
    ? [
        {
          id: 'cuttack_apex',
          position: [20.46, 85.88] as [number, number],
          title: 'Cuttack (Delta Apex)',
          subtitle: 'Mahanadi Basin Hydro Hub',
          color: '#008080',
          badge: 'A',
        },
        {
          id: 'sambalpur_hirakud',
          position: [21.52, 83.87] as [number, number],
          title: 'Hirakud Dam / Sambalpur',
          subtitle: 'Upper Basin Control',
          color: '#1a56db',
          badge: 'H',
        },
        {
          id: 'paradip_port',
          position: [20.31, 86.61] as [number, number],
          title: 'Paradip (Estuary Mouth)',
          subtitle: 'Bay of Bengal Outflow',
          color: '#f59e0b',
          badge: 'P',
        },
      ]
    : [
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

  return (
    <LeafletMap
      center={effectiveCenter}
      zoom={effectiveZoom}
      height={height}
      className={className}
      floodIntensityMultiplier={isMahanadi ? 0 : floodIntensityMultiplier}
      polylines={polylines}
      polygons={[]}
      markers={markers}
    />
  );
};

export default MapContainer;
