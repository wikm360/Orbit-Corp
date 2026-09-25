"use client";

import {
  AriaAttributes,
  ButtonHTMLAttributes,
  CSSProperties,
  KeyboardEvent,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

import { cn } from "@/shared/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
  description?: string | null;
  disabled?: boolean;
}

interface MenuPosition {
  top?: number;
  bottom?: number;
  left: number;
  width: number;
  maxHeight: number;
}

interface SelectProps extends Pick<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "autoFocus" | "aria-label" | "aria-labelledby" | "aria-describedby"
> {
  id?: string;
  value: string;
  options: readonly SelectOption[];
  onValueChange: (value: string) => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  name?: string;
  placeholder?: string;
  emptyLabel?: string;
  searchPlaceholder?: string;
  searchable?: boolean;
  size?: "sm" | "md";
}

function normalize(value: string) {
  return value.trim().toLocaleLowerCase("fa-IR");
}

export function Select({
  id,
  value,
  options,
  onValueChange,
  className,
  disabled = false,
  required = false,
  name,
  placeholder = "انتخاب کنید",
  emptyLabel = "گزینه‌ای پیدا نشد",
  searchPlaceholder = "جست‌وجو…",
  searchable: searchableProp,
  size = "md",
  autoFocus,
  "aria-label": ariaLabel,
  "aria-labelledby": ariaLabelledBy,
  "aria-describedby": ariaDescribedBy,
}: SelectProps) {
  const generatedId = useId();
  const listboxId = `${generatedId}-listbox`;
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeValue, setActiveValue] = useState<string | null>(null);
  const [position, setPosition] = useState<MenuPosition>({ left: 8, width: 240, maxHeight: 320 });
  const searchable = searchableProp ?? options.length > 7;
  const selectedOption = options.find((option) => option.value === value);
  const filteredOptions = useMemo(() => {
    const normalizedQuery = normalize(query);
    if (!normalizedQuery) return [...options];
    return options.filter((option) => normalize(`${option.label} ${option.description ?? ""}`).includes(normalizedQuery));
  }, [options, query]);
  const resolvedActiveValue = filteredOptions.some((option) => option.value === activeValue && !option.disabled)
    ? activeValue
    : firstEnabled(filteredOptions);
  const activeIndex = filteredOptions.findIndex((option) => option.value === resolvedActiveValue);
  const activeDescendant = activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined;

  function updatePosition() {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const viewportPadding = 8;
    const desiredWidth = Math.max(rect.width, 240);
    const width = Math.min(desiredWidth, window.innerWidth - viewportPadding * 2);
    const left = Math.min(
      Math.max(rect.right - width, viewportPadding),
      window.innerWidth - width - viewportPadding
    );
    const roomBelow = window.innerHeight - rect.bottom - 12;
    const roomAbove = rect.top - 12;
    const openAbove = roomBelow < 220 && roomAbove > roomBelow;
    const availableRoom = openAbove ? roomAbove : roomBelow;
    setPosition({
      ...(openAbove
        ? { bottom: window.innerHeight - rect.top + 8 }
        : { top: rect.bottom + 8 }),
      left,
      width,
      maxHeight: Math.max(140, Math.min(320, availableRoom)),
    });
  }

  function firstEnabled(list: readonly SelectOption[], reverse = false) {
    const candidates = reverse ? [...list].reverse() : list;
    return candidates.find((option) => !option.disabled)?.value ?? null;
  }

  function openMenu(preferLast = false) {
    if (disabled) return;
    updatePosition();
    setQuery("");
    setActiveValue(
      options.some((option) => option.value === value && !option.disabled)
        ? value
        : firstEnabled(options, preferLast)
    );
    setIsOpen(true);
  }

  function closeMenu({ restoreFocus = false } = {}) {
    setIsOpen(false);
    setQuery("");
    if (restoreFocus) requestAnimationFrame(() => triggerRef.current?.focus());
  }

  function choose(option: SelectOption) {
    if (option.disabled) return;
    onValueChange(option.value);
    closeMenu({ restoreFocus: true });
  }

  function moveActive(step: 1 | -1) {
    const enabled = filteredOptions.filter((option) => !option.disabled);
    if (enabled.length === 0) return;
    const currentIndex = enabled.findIndex((option) => option.value === resolvedActiveValue);
    const nextIndex = currentIndex < 0
      ? step === 1 ? 0 : enabled.length - 1
      : (currentIndex + step + enabled.length) % enabled.length;
    setActiveValue(enabled[nextIndex]?.value ?? null);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (!isOpen) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
        event.preventDefault();
        openMenu(event.key === "ArrowUp");
      }
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu({ restoreFocus: true });
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      moveActive(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveActive(-1);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActiveValue(firstEnabled(filteredOptions));
    } else if (event.key === "End") {
      event.preventDefault();
      setActiveValue(firstEnabled(filteredOptions, true));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const activeOption = filteredOptions.find((option) => option.value === resolvedActiveValue);
      if (activeOption) choose(activeOption);
    } else if (event.key === "Tab") {
      closeMenu();
    }
  }

  useEffect(() => {
    if (!isOpen) return;
    updatePosition();
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target) && !menuRef.current?.contains(target)) closeMenu();
    };
    const handleViewportChange = () => updatePosition();
    document.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && searchable) requestAnimationFrame(() => searchRef.current?.focus());
  }, [isOpen, searchable]);

  useEffect(() => {
    if (!disabled || !isOpen) return;
    const frame = requestAnimationFrame(() => closeMenu());
    return () => cancelAnimationFrame(frame);
  }, [disabled, isOpen]);

  const portalStyle: CSSProperties = {
    position: "fixed",
    top: position.top,
    bottom: position.bottom,
    left: position.left,
    width: position.width,
    maxHeight: position.maxHeight,
  };
  const sharedAria: AriaAttributes = {
    "aria-label": ariaLabel,
    "aria-labelledby": ariaLabelledBy,
    "aria-describedby": ariaDescribedBy,
  };

  return (
    <div ref={rootRef} className={cn("relative min-w-0", className)}>
      {name && <input type="hidden" name={name} value={value} />}
      <button
        ref={triggerRef}
        id={id}
        type="button"
        role="combobox"
        autoFocus={autoFocus}
        disabled={disabled}
        aria-controls={listboxId}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-activedescendant={isOpen && !searchable ? activeDescendant : undefined}
        aria-required={required || undefined}
        {...sharedAria}
        onClick={() => isOpen ? closeMenu() : openMenu()}
        onKeyDown={handleKeyDown}
        className={cn(
          "group flex w-full items-center gap-2.5 rounded-xl border border-slate-200 bg-white pr-3 pl-2.5 text-right text-slate-700 shadow-sm outline-none transition duration-200 hover:border-teal-300 hover:shadow-md focus-visible:border-teal-500 focus-visible:ring-4 focus-visible:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none",
          size === "sm" ? "h-9 text-xs" : "h-11 text-sm",
          isOpen && "border-teal-500 ring-4 ring-teal-100"
        )}
      >
        <span className={cn(
          "grid shrink-0 place-items-center rounded-lg bg-teal-50 text-teal-700 transition group-hover:bg-teal-100",
          size === "sm" ? "h-6 w-6" : "h-7 w-7"
        )} aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="m5 12 4 4L19 6" />
          </svg>
        </span>
        <span className={cn("min-w-0 flex-1 truncate font-medium", !selectedOption && "text-slate-400")}>
          {selectedOption?.label ?? placeholder}
        </span>
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg text-slate-400 transition group-hover:bg-slate-50 group-hover:text-teal-700" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={cn("h-4 w-4 transition-transform duration-200", isOpen && "rotate-180")}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m7 10 5 5 5-5" />
          </svg>
        </span>
      </button>

      {isOpen && typeof document !== "undefined" && createPortal(
        <div
          ref={menuRef}
          style={portalStyle}
          dir="rtl"
          className="z-[1000] flex animate-[select-in_140ms_ease-out] flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white/95 p-1.5 shadow-[0_22px_60px_-18px_rgba(15,23,42,0.38)] ring-1 ring-black/[0.03] backdrop-blur-xl"
        >
          {searchable && (
            <label className="relative mb-1.5 block shrink-0">
              <span className="sr-only">جست‌وجو در گزینه‌ها</span>
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400">
                <circle cx="11" cy="11" r="7" /><path strokeLinecap="round" d="m20 20-4-4" />
              </svg>
              <input
                ref={searchRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                aria-controls={listboxId}
                aria-activedescendant={activeDescendant}
                placeholder={searchPlaceholder}
                className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 pr-9 pl-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-teal-400 focus:bg-white focus:ring-4 focus:ring-teal-100"
              />
            </label>
          )}
          <div id={listboxId} role="listbox" aria-label={ariaLabel} className="min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain p-0.5">
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-8 text-center text-xs text-slate-400">{emptyLabel}</div>
            ) : filteredOptions.map((option, index) => {
              const selected = option.value === value;
              const active = option.value === resolvedActiveValue;
              return (
                <button
                  key={option.value}
                  id={`${listboxId}-option-${index}`}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  disabled={option.disabled}
                  tabIndex={-1}
                  onPointerMove={() => { if (!option.disabled) setActiveValue(option.value); }}
                  onClick={() => choose(option)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-right text-sm outline-none transition disabled:cursor-not-allowed disabled:opacity-40",
                    selected ? "bg-teal-50 text-teal-800" : active ? "bg-slate-100 text-slate-900" : "text-slate-600 hover:bg-slate-50"
                  )}
                >
                  <span className={cn(
                    "grid h-5 w-5 shrink-0 place-items-center rounded-full border transition",
                    selected ? "border-teal-500 bg-teal-600 text-white" : "border-slate-200 bg-white text-transparent"
                  )} aria-hidden="true">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.2" className="h-3 w-3"><path strokeLinecap="round" strokeLinejoin="round" d="m4.5 10 3.3 3.3L15.5 6" /></svg>
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{option.label}</span>
                    {option.description && <span className="mt-0.5 block truncate text-[11px] leading-5 text-slate-400">{option.description}</span>}
                  </span>
                  {selected && <span className="text-[10px] font-semibold text-teal-600">انتخاب‌شده</span>}
                </button>
              );
            })}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
