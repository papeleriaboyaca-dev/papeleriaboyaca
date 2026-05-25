// Mapping slug → emoji. Si tu categoría no aparece, agregá la entrada acá.
// El slug se compara en lowercase; fallback "🛒".
const CATEGORY_EMOJI: Record<string, string> = {
  cuadernos: "📓",
  utiles: "📚",
  "utiles-escolares": "🎒",
  escolar: "🎒",
  lapices: "✏️",
  arte: "🎨",
  artes: "🎨",
  carpetas: "📁",
  oficina: "💼",
  manualidades: "🖍️",
  papel: "📄",
  impresion: "🖨️",
  organizacion: "📋",
  colores: "🖌️",
  marcadores: "🖊️",
  boligrafos: "🖊️",
  tijeras: "✂️",
  pegamento: "🧴",
  calculadora: "🧮",
  calculadoras: "🧮",
  mochilas: "🎒",
  libros: "📖",
  juegos: "🎲",
  regalos: "🎁",
};

export function categoryEmoji(slug?: string): string {
  if (!slug) return "🛒";
  return CATEGORY_EMOJI[slug.toLowerCase()] ?? "🛒";
}
