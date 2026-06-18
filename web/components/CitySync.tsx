"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useApp } from "@/lib/store";

/** Keep the shared city store aligned with ?city= in the URL (bookmarks, back button). */
function CitySyncInner() {
  const params = useSearchParams();
  const setCity = useApp((s) => s.setCity);

  useEffect(() => {
    const urlCity = params.get("city");
    if (urlCity) setCity(urlCity);
  }, [params, setCity]);

  return null;
}

export function CitySync() {
  return (
    <Suspense fallback={null}>
      <CitySyncInner />
    </Suspense>
  );
}
