import { cn } from "@/shared/lib/utils";

const paths = {
  spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/><path d="m20 2 .6 1.4L22 4l-1.4.6L20 6l-.6-1.4L18 4l1.4-.6L20 2Z"/></>,
  document: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
  memory: <><path d="M8 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2M9 3h6v4H9zM8 12h8M8 16h5"/></>,
  people: <><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M21 21v-3a6 6 0 0 0-3-5"/></>,
  edit: <><path d="m16 3 5 5M4 15 16 3a2 2 0 0 1 5 5L9 20l-6 1 1-6Z"/></>,
  arrow: <path d="M19 12H5m6-6-6 6 6 6"/>,
  check: <path d="m5 12 4 4L19 6"/>,
  folder: <path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>,
  plus: <path d="M12 5v14M5 12h14"/>,
} as const;

export type OrbitIconName = keyof typeof paths;

export function OrbitIcon({ name, className }: { name: OrbitIconName; className?: string }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={cn("h-5 w-5 shrink-0", className)}>{paths[name]}</svg>;
}
