const LEVELS = ["low", "medium", "high"] as const;

export type ImpactLevel = (typeof LEVELS)[number];

export function ImpactTag({ level }: { level: ImpactLevel }) {
  return <span className={`tag tag-${level}`}>{level}</span>;
}

