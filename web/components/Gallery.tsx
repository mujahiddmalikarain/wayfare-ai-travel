"use client";

/** Inside Airbnb exposes one picture_url per listing, so we present a framed
 *  hero rather than faking a multi-photo gallery. Swap to a carousel when a
 *  richer photo source is wired in. */
export function Gallery({ photo, name }: { photo?: string; name: string }) {
  return (
    <div className="relative aspect-[16/9] w-full overflow-hidden rounded-xl2 bg-brand-soft">
      {photo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={photo} alt={name} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full items-center justify-center text-muted">No photo available</div>
      )}
    </div>
  );
}
