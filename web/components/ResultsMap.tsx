"use client";

import { useEffect, useRef } from "react";
import maplibregl, { Map as MlMap, GeoJSONSource, type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useApp } from "@/lib/store";
import type { Listing } from "@/lib/types";

interface Props {
  listings: Listing[];
  /** Changes only on a *new search*, so we refit bounds then but not on pan. */
  fitKey: string;
}

const STYLE: StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const toGeoJSON = (listings: Listing[]) => ({
  type: "FeatureCollection" as const,
  features: listings
    .filter((l) => l.lat != null && l.lng != null)
    .map((l) => ({
      type: "Feature" as const,
      id: l.id,
      geometry: { type: "Point" as const, coordinates: [l.lng!, l.lat!] },
      properties: { price: Math.round(l.price ?? 0) },
    })),
});

export function ResultsMap({ listings, fitKey }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);
  const ready = useRef(false);
  const lastHover = useRef<number | null>(null);
  const setHovered = useApp((s) => s.setHovered);
  const setBounds = useApp((s) => s.setBounds);
  const hoveredId = useApp((s) => s.hoveredId);

  // init once
  useEffect(() => {
    if (!ref.current || map.current) return;
    const m = new maplibregl.Map({
      container: ref.current,
      style: STYLE,
      center: [-9.139, 38.722],
      zoom: 11,
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    m.on("load", () => {
      m.addSource("listings", {
        type: "geojson",
        data: toGeoJSON(listings),
        cluster: true,
        clusterRadius: 50,
      });

      m.addLayer({
        id: "clusters", type: "circle", source: "listings", filter: ["has", "point_count"],
        paint: {
          "circle-color": "#1f3a5f",
          "circle-radius": ["step", ["get", "point_count"], 16, 25, 22, 100, 30],
          "circle-stroke-width": 3, "circle-stroke-color": "#ffffff",
        },
      });
      m.addLayer({
        id: "cluster-count", type: "symbol", source: "listings", filter: ["has", "point_count"],
        layout: { "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Noto Sans Regular"], "text-size": 13 },
        paint: { "text-color": "#ffffff" },
      });
      m.addLayer({
        id: "point", type: "circle", source: "listings", filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-radius": ["case", ["boolean", ["feature-state", "hover"], false], 9, 6],
          "circle-color": ["case", ["boolean", ["feature-state", "hover"], false], "#1f3a5f", "#d9883a"],
          "circle-stroke-width": 2, "circle-stroke-color": "#ffffff",
        },
      });
      m.addLayer({
        id: "price", type: "symbol", source: "listings", filter: ["!", ["has", "point_count"]],
        layout: {
          "text-field": ["concat", "€", ["to-string", ["get", "price"]]],
          "text-font": ["Noto Sans Regular"], "text-size": 11, "text-offset": [0, -1.4],
          "text-anchor": "bottom",
        },
        paint: { "text-color": "#16243d", "text-halo-color": "#ffffff", "text-halo-width": 1.5 },
      });

      m.on("mouseenter", "point", (e) => {
        m.getCanvas().style.cursor = "pointer";
        const id = e.features?.[0]?.id as number | undefined;
        if (id != null) setHovered(id);
      });
      m.on("mouseleave", "point", () => {
        m.getCanvas().style.cursor = "";
        setHovered(null);
      });
      m.on("click", "clusters", async (e) => {
        const f = m.queryRenderedFeatures(e.point, { layers: ["clusters"] })[0];
        const src = m.getSource("listings") as GeoJSONSource;
        const zoom = await src.getClusterExpansionZoom(f.properties!.cluster_id);
        m.easeTo({ center: (f.geometry as any).coordinates, zoom });
      });

      const emitBounds = () => {
        const b = m.getBounds();
        setBounds({ west: b.getWest(), south: b.getSouth(), east: b.getEast(), north: b.getNorth() });
      };
      m.on("moveend", emitBounds);
      ready.current = true;
      fit();
    });

    return () => { m.remove(); map.current = null; ready.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // update data
  useEffect(() => {
    if (!ready.current || !map.current) return;
    (map.current.getSource("listings") as GeoJSONSource)?.setData(toGeoJSON(listings) as any);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listings]);

  // refit only on new search
  useEffect(() => { fit(); /* eslint-disable-next-line */ }, [fitKey]);

  // card -> map hover highlight
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    if (lastHover.current != null)
      m.setFeatureState({ source: "listings", id: lastHover.current }, { hover: false });
    if (hoveredId != null)
      m.setFeatureState({ source: "listings", id: hoveredId }, { hover: true });
    lastHover.current = hoveredId;
  }, [hoveredId]);

  function fit() {
    const m = map.current;
    if (!m || !ready.current) return;
    const pts = listings.filter((l) => l.lat != null && l.lng != null);
    if (pts.length === 0) return;
    const b = new maplibregl.LngLatBounds();
    pts.forEach((l) => b.extend([l.lng!, l.lat!]));
    m.fitBounds(b, { padding: 60, maxZoom: 15, duration: 600 });
  }

  return <div ref={ref} className="h-full w-full rounded-xl2" />;
}
