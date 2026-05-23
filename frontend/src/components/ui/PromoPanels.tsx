import type { MarketingContent } from "@/types";

interface PromoPanelsProps {
  items: MarketingContent[];
}

export default function PromoPanels({ items }: PromoPanelsProps) {
  if (items.length === 0) return null;

  const displayed = items.slice(0, 4);

  return (
    <section className="container mx-auto px-4 pb-12">
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
            className="overflow-hidden rounded-xl bg-[#263238] shadow-sm hover:shadow-md transition-shadow"
            style={{ aspectRatio: "16 / 9" }}
          >
            <img
              src={item.image_url}
              alt={item.title}
              className="w-full h-full object-cover hover:scale-105 transition-transform duration-400"
            />
          </div>
        ))}
      </div>
    </section>
  );
}
