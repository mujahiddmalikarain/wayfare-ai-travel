"use client";

import { useEffect, useRef } from "react";
import maplibregl, { Map as MlMap, type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const STYLE: StyleSpecification = {
  version: 8,
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

export function MiniMap({ lat, lng }: { lat: number; lng: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);

  useEffect(() => {
    if (!ref.current || map.current) return;
    const m = new maplibregl.Map({
      container: ref.current, style: STYLE, center: [lng, lat], zoom: 14,
      interactive: true, attributionControl: false,
    });
    new maplibregl.Marker({ color: "#d9883a" }).setLngLat([lng, lat]).addTo(m);
    map.current = m;
    return () => { m.remove(); map.current = null; };
  }, [lat, lng]);

  return <div ref={ref} className="h-64 w-full overflow-hidden rounded-xl2 border border-line" />;
}
