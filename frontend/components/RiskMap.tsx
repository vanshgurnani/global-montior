"use client";

import { useEffect, useMemo, useState } from "react";

import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from "react-simple-maps";

import { api, type CountryRisk, type MapLayerPoint } from "@/lib/api";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

function riskColor(value: number): string {
  if (value >= 0.66) return "#c0392b";
  if (value >= 0.33) return "#e67e22";
  if (value > 0) return "#f4d03f";
  return "#2c3e50";
}

function normalizedIntensity(value: unknown, fallback: number = 1): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.min(4, n));
}

type LayerKey = "war" | "nuclear" | "bunkers" | "chokepoints";

type MarkerPoint = {
  id: string;
  name: string;
  coords: [number, number];
  note: string;
  source: string;
  layer: LayerKey;
  intensity: number;
};

const LAYER_STYLES: Record<LayerKey, { label: string; color: string }> = {
  war: { label: "War Zones", color: "#ef4444" },
  nuclear: { label: "Nuclear Sites", color: "#f59e0b" },
  bunkers: { label: "Bunkers", color: "#3b82f6" },
  chokepoints: { label: "Chokepoints", color: "#22c55e" },
};

const STATIC_POINTS: MarkerPoint[] = [
  { id: "ukr", name: "Ukraine Front", coords: [31.2, 48.4], note: "Ongoing war theater", source: "https://www.crisisgroup.org/europe-central-asia/eastern-europe/ukraine", layer: "war", intensity: 2.5 },
  { id: "gaza", name: "Gaza-Israel", coords: [34.3, 31.4], note: "Active conflict zone", source: "https://www.crisisgroup.org/middle-east-north-africa/east-mediterranean-mena/israelpalestine", layer: "war", intensity: 2.2 },
  { id: "sudan", name: "Sudan", coords: [30.2, 15.5], note: "Civil war hotspot", source: "https://www.crisisgroup.org/africa/horn-africa/sudan", layer: "war", intensity: 2.0 },
  { id: "zap", name: "Zaporizhzhia NPP", coords: [34.6, 47.5], note: "Nuclear facility in conflict region", source: "https://www.iaea.org/newscenter/focus/ukraine", layer: "nuclear", intensity: 1.8 },
  { id: "natanz", name: "Natanz Facility", coords: [51.7, 33.7], note: "Major enrichment site (open-source)", source: "https://www.iaea.org", layer: "nuclear", intensity: 1.7 },
  { id: "deqing", name: "China Silo Fields", coords: [96.2, 40.0], note: "Strategic missile/nuclear expansion reports", source: "https://fas.org/issues/nuclear-weapons/status-world-nuclear-forces/", layer: "nuclear", intensity: 1.6 },
  { id: "cheyenne", name: "Cheyenne Mountain", coords: [-104.84, 38.74], note: "Hardened command bunker", source: "https://www.norad.mil", layer: "bunkers", intensity: 1.3 },
  { id: "kosvinsky", name: "Kosvinsky Mountain", coords: [59.3, 59.7], note: "Reported strategic bunker complex", source: "https://missilethreat.csis.org", layer: "bunkers", intensity: 1.3 },
  { id: "yanan", name: "Underground Defense Hubs", coords: [109.0, 36.5], note: "Open-source strategic underground sites", source: "https://www.csis.org", layer: "bunkers", intensity: 1.2 },
  { id: "hormuz", name: "Strait of Hormuz", coords: [56.5, 26.6], note: "Global oil chokepoint", source: "https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints", layer: "chokepoints", intensity: 1.5 },
  { id: "suez", name: "Suez Canal", coords: [32.55, 30.5], note: "Critical maritime route", source: "https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints", layer: "chokepoints", intensity: 1.5 },
  { id: "malacca", name: "Strait of Malacca", coords: [101.0, 2.5], note: "Asia-Pacific trade chokepoint", source: "https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints", layer: "chokepoints", intensity: 1.4 },
];

export function RiskMap({ countries }: { countries: CountryRisk[] }) {
  const byName = new Map(countries.map((c) => [c.country.toLowerCase(), c.avg_war_risk]));
  const [position, setPosition] = useState({ coordinates: [10, 20] as [number, number], zoom: 1.08 });
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [enabledLayers, setEnabledLayers] = useState<Record<LayerKey, boolean>>({
    war: true,
    nuclear: false,
    bunkers: false,
    chokepoints: false,
  });
  const [selectedPoint, setSelectedPoint] = useState<MarkerPoint | null>(null);
  const [mapPoints, setMapPoints] = useState<MarkerPoint[]>(STATIC_POINTS);
  const [updatedAt, setUpdatedAt] = useState<string>("static fallback");

  const topLabel = useMemo(() => {
    if (!countries.length) return "No country risk data yet";
    const top = countries.reduce((best, c) => (c.avg_war_risk > best.avg_war_risk ? c : best));
    return `Top risk: ${top.country} (${(top.avg_war_risk * 100).toFixed(1)}%)`;
  }, [countries]);

  const zoomIn = () => setPosition((p) => ({ ...p, zoom: Math.min(4, p.zoom + 0.25) }));
  const zoomOut = () => setPosition((p) => ({ ...p, zoom: Math.max(1, p.zoom - 0.25) }));
  const resetView = () => setPosition({ coordinates: [10, 20], zoom: 1.08 });
  const visiblePoints = mapPoints.filter((p) => enabledLayers[p.layer]);

  useEffect(() => {
    const toMarkers = (points: MapLayerPoint[], layer: LayerKey): MarkerPoint[] =>
      points.map((p) => ({
        id: `${layer}-${p.id}`,
        name: p.name,
        coords: [p.lon, p.lat],
        note: `Live signal intensity: ${Number(p.intensity || 0).toFixed(2)}`,
        source: p.source,
        layer,
        intensity: normalizedIntensity(p.intensity, 1),
      }));

    api
      .getMapLayers()
      .then((data) => {
        const merged = [
          ...toMarkers(data.war_zones || [], "war"),
          ...toMarkers(data.nuclear_sites || [], "nuclear"),
          ...toMarkers(data.bunkers || [], "bunkers"),
          ...toMarkers(data.chokepoints || [], "chokepoints"),
        ];
        if (merged.length > 0) {
          setMapPoints(merged);
          setUpdatedAt(data.updated_at ? new Date(data.updated_at).toLocaleString() : "live");
        }
      })
      .catch(() => {
        // Keep static fallback markers when live map layer fetch fails.
      });
  }, []);

  return (
    <div className="card map-card">
      <div className="map-header">
        <h3>Global Risk Heatmap</h3>
        <span className="map-caption">{topLabel} | Map data: {updatedAt}</span>
      </div>
      <div className="map-controls">
        <button type="button" onClick={zoomOut}>-</button>
        <button type="button" onClick={resetView}>Reset</button>
        <button type="button" onClick={zoomIn}>+</button>
      </div>
      <div className="map-filters">
        <button
          type="button"
          className={showHeatmap ? "map-chip active" : "map-chip"}
          onClick={() => setShowHeatmap((v) => !v)}
        >
          Heatmap
        </button>
        {(Object.keys(LAYER_STYLES) as LayerKey[]).map((layer) => (
          <button
            key={layer}
            type="button"
            className={enabledLayers[layer] ? "map-chip active" : "map-chip"}
            onClick={() => setEnabledLayers((prev) => ({ ...prev, [layer]: !prev[layer] }))}
          >
            {LAYER_STYLES[layer].label}
          </button>
        ))}
      </div>
      <div className="map-stage">
        <ComposableMap projection="geoMercator" projectionConfig={{ scale: 180 }}>
          <ZoomableGroup
            center={position.coordinates}
            zoom={position.zoom}
            onMoveEnd={(next: any) =>
              setPosition({
                coordinates: next.coordinates as [number, number],
                zoom: next.zoom,
              })
            }
          >
            <Geographies geography={GEO_URL}>
              {({ geographies }: { geographies: any[] }) =>
                geographies.map((geo: any) => {
                  const name = (geo.properties.name as string).toLowerCase();
                  const risk = byName.get(name) ?? 0;
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill={showHeatmap ? riskColor(risk) : "#1f2937"}
                      stroke="#071021"
                      strokeWidth={0.3}
                    />
                  );
                })
              }
            </Geographies>
            {visiblePoints.map((point) => (
              <Marker key={point.id} coordinates={point.coords}>
                <g onClick={() => setSelectedPoint(point)} style={{ cursor: "pointer" }}>
                  {(() => {
                    const i = normalizedIntensity(point.intensity, 1);
                    return (
                      <>
                        <circle
                          r={6 + i * 3.6}
                          fill={LAYER_STYLES[point.layer].color}
                          opacity={0.2}
                          stroke="none"
                        />
                        <circle
                          r={3.6 + i * 0.6}
                          fill={LAYER_STYLES[point.layer].color}
                          opacity={0.85}
                          stroke="#0b1020"
                          strokeWidth={1.1}
                        />
                      </>
                    );
                  })()}
                </g>
              </Marker>
            ))}
          </ZoomableGroup>
        </ComposableMap>
      </div>
      <div className="map-legend">
        {(Object.keys(LAYER_STYLES) as LayerKey[]).map((layer) => (
          <span key={layer}>
            <i style={{ backgroundColor: LAYER_STYLES[layer].color }} />
            {LAYER_STYLES[layer].label}
          </span>
        ))}
      </div>
      {selectedPoint ? (
        <p className="map-point-info">
          <strong>{selectedPoint.name}</strong>: {selectedPoint.note}.{" "}
          <a href={selectedPoint.source} target="_blank" rel="noreferrer">
            Source
          </a>
        </p>
      ) : null}
    </div>
  );
}
