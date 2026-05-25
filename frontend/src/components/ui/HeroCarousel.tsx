import type { MarketingContent } from "@/types";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface HeroCarouselProps {
  items: MarketingContent[];
}

export default function HeroCarousel({ items }: HeroCarouselProps) {
  const [current, setCurrent] = useState(0);
  const [paused, setPaused] = useState(false);
  const startX = useRef<number | null>(null);
  const total = items.length;

  const next = useCallback(() => setCurrent((c) => (c + 1) % total), [total]);
  const prev = useCallback(
    () => setCurrent((c) => (c - 1 + total) % total),
    [total],
  );

  useEffect(() => {
    if (total <= 1 || paused) return;
    const id = setInterval(next, 5000);
    return () => clearInterval(id);
  }, [total, paused, next]);

  if (total === 0) return null;

  const handlePointerDown = (e: React.PointerEvent) => {
    startX.current = e.clientX;
  };
  const handlePointerUp = (e: React.PointerEvent) => {
    if (startX.current === null) return;
    const dx = e.clientX - startX.current;
    if (Math.abs(dx) > 50) {
      if (dx < 0) {
        next();
      } else {
        prev();
      }
    }
    startX.current = null;
  };

  return (
    <div
      className="relative overflow-hidden select-none w-full"
      style={{ height: "min(33.33vw, 480px)" }}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* Track — ancho explícito para que translateX sea predecible */}
      <div
        className="flex h-full transition-transform duration-500 ease-in-out"
        style={{
          width: `${total * 100}%`,
          transform: `translateX(-${(current / total) * 100}%)`,
        }}
      >
        {items.map((item) => (
          <div
            key={item.id}
            className="relative h-full bg-[#263238] flex items-center justify-center overflow-hidden"
            style={{ width: `${100 / total}%` }}
          >
            <span className="text-white/40 text-sm font-medium px-4 text-center select-none">
              {item.title}
            </span>
            {item.image_url && (
              <img
                src={item.image_url}
                alt={item.title}
                className="absolute inset-0 w-full h-full object-cover"
                draggable={false}
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            )}
          </div>
        ))}
      </div>

      {/* Arrows — only when more than 1 slide */}
      {total > 1 && (
        <>
          <button
            onClick={prev}
            className="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/30 hover:bg-black/50 text-white flex items-center justify-center transition backdrop-blur-sm"
            aria-label="Anterior"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            onClick={next}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/30 hover:bg-black/50 text-white flex items-center justify-center transition backdrop-blur-sm"
            aria-label="Siguiente"
          >
            <ChevronRight size={20} />
          </button>

          {/* Dots */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {items.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`transition-all rounded-full ${
                  i === current
                    ? "w-6 h-2 bg-white"
                    : "w-2 h-2 bg-white/50 hover:bg-white/75"
                }`}
                aria-label={`Ir a slide ${i + 1}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
