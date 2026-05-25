import type { MarketingContent } from "@/types";

interface PromoPanelsProps {
  items: MarketingContent[];
}

export default function PromoPanels({ items }: PromoPanelsProps) {
  if (items.length === 0) return null;

  const displayed = items.slice(0, 4);

  // Con pocos paneles a aspect 16/9 cada uno domina la página. Bajamos altura para 1-2.
  const aspectRatio = displayed.length === 1 ? "21 / 9" : "16 / 9";
  const maxHeight =
    displayed.length === 1 ? 280 : displayed.length === 2 ? 220 : undefined;

  return (
    <section className="container mx-auto px-4 py-12">
      <div
        className={`grid gap-4 ${
          displayed.length === 1
            ? "grid-cols-1"
            : displayed.length === 2
            ? "grid-cols-1 sm:grid-cols-2"
            : displayed.length === 3
            ? "grid-cols-1 sm:grid-cols-3"
            : "grid-cols-2 sm:grid-cols-2 lg:grid-cols-4"
        }`}
      >
        {displayed.map((item) => (
          <div
            key={item.id}
            className="overflow-hidden rounded-xl bg-[#263238] shadow-sm hover:shadow-md transition-shadow flex items-center justify-center relative mx-auto w-full"
            style={{ aspectRatio, maxHeight }}
          >
            <span className="text-white/40 text-sm font-medium px-4 text-center">
              {item.title}
            </span>
            {item.image_url && (
              <img
                src={item.image_url}
                alt={item.title}
                className="absolute inset-0 w-full h-full object-cover hover:scale-105 transition-transform duration-400"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
