/* eslint-disable @next/next/no-img-element */
"use client"

import type { KeyboardEvent, ReactNode } from "react"
import {
  BatteryFull,
  Calendar,
  House,
  WandSparkles,
  type LucideIcon,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * Templates — the "what you can make" examples. A `TemplateItem` seeds the
 * prompt dock (prompt text + optional model/settings) when its Try action fires.
 * `TemplateCard` and `ExamplePresets` render them; the Explore tab on Home uses
 * `ExamplePresets`.
 */

// KMI preview art in /presets/*.svg.
const THUMBS = [
  "/presets/kmi-camp-1.svg",
  "/presets/kmi-camp-2.svg",
  "/presets/kmi-camp-3.svg",
  "/presets/kmi-camp-4.svg",
] as const

export interface TemplateItem {
  id: string
  title: string
  subtitle: string
  /** Free-form filter category used by the picker tabs. */
  category: string
  kind: "image" | "video"
  images: [string, string, string]
  icon: LucideIcon
  /** What the Try action puts in the dock. */
  prompt: string
  /** Catalog model id to switch to, when the template needs a specific one. */
  modelId?: string
  settings?: Record<string, unknown>
}

export const TEMPLATES: TemplateItem[] = [
  {
    id: "camp-key-visual",
    title: "Camp key visual",
    subtitle: "Global health leadership camp",
    category: "event",
    kind: "image",
    images: [THUMBS[0], THUMBS[2], THUMBS[3]],
    icon: Calendar,
    prompt:
      "Key visual for a global health leadership camp: a luminous globe woven with medical and network motifs, deep navy and teal palette, clean modern editorial style, space for a title.",
  },
  {
    id: "speaker-portrait",
    title: "Speaker portrait",
    subtitle: "Polished keynote speaker photo",
    category: "speaker",
    kind: "image",
    images: [THUMBS[1], THUMBS[0], THUMBS[3]],
    icon: WandSparkles,
    prompt:
      "Professional portrait of a healthcare expert on stage, soft key light, shallow depth of field, confident and approachable, dark conference backdrop.",
  },
  {
    id: "popup-poster",
    title: "Event pop-up poster",
    subtitle: "Web notice banner",
    category: "event",
    kind: "image",
    images: [THUMBS[2], THUMBS[0], THUMBS[1]],
    icon: BatteryFull,
    prompt:
      "Web pop-up poster for an international health policy camp, bold typography area, teal and gold accents, minimal geometric globe, crisp flat design.",
  },
  {
    id: "camp-atmosphere",
    title: "Camp atmosphere",
    subtitle: "Warm, candid group moment",
    category: "mood",
    kind: "image",
    images: [THUMBS[3], THUMBS[1], THUMBS[2]],
    icon: House,
    prompt:
      "Candid photo of young health professionals networking at a leadership camp, golden hour light, film grain, warm and energetic mood.",
  },
]

function gradientFromSeed(seed: string): string {
  let hash = 0
  for (const c of seed) hash = (hash * 31 + c.charCodeAt(0)) >>> 0
  const start = hash % 360
  const end = (start + 36 + ((hash >>> 8) % 72)) % 360
  return `linear-gradient(135deg, hsl(${start} 62% 52%) 0%, hsl(${end} 76% 27%) 100%)`
}

function GradientBadge({ as: Glyph, seed }: { as: LucideIcon; seed: string }) {
  return (
    <span className="relative flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-[10px] border border-white/25 text-white shadow-[0_5px_3px_rgba(0,0,0,0.08),inset_0_3px_5px_rgba(255,255,255,0.24)]">
      <span
        aria-hidden
        className="absolute inset-0"
        style={{ backgroundImage: gradientFromSeed(seed) }}
      />
      <span
        aria-hidden
        className="absolute inset-0 bg-gradient-to-t from-transparent to-white/20 mix-blend-overlay"
      />
      <Glyph className="relative size-5" />
    </span>
  )
}

const TRIPTYCH = [
  "rounded-l-2xl rounded-r-sm",
  "rounded-sm",
  "rounded-r-2xl rounded-l-sm",
] as const

export interface TemplateCardProps {
  template: TemplateItem
  variant?: "single" | "triptych"
  onTry: (template: TemplateItem) => void
  tryLabel?: ReactNode
}

export function TemplateCard({
  template,
  variant = "single",
  onTry,
  tryLabel = "Try",
}: TemplateCardProps) {
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.currentTarget !== event.target) return
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      onTry(template)
    }
  }
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Use template: ${template.title}`}
      className="relative flex cursor-pointer flex-col gap-2 rounded-[20px] bg-white/5 p-2 shadow-[0_2px_6px_rgba(0,0,0,0.15)] transition-[transform,background-color] duration-200 hover:z-[1] hover:-translate-y-0.5 hover:bg-white/8 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none motion-reduce:hover:translate-y-0"
      onClick={() => onTry(template)}
      onKeyDown={onKeyDown}
    >
      <div className="flex h-60 items-stretch gap-1.5">
        {variant === "triptych" ? (
          template.images.map((src, i) => (
            <div
              key={i}
              className={cn(
                "min-w-0 flex-1 overflow-hidden border border-white/10",
                TRIPTYCH[i]
              )}
            >
              <img
                src={src}
                alt={`${template.title} — shot ${i + 1}`}
                className="size-full object-cover"
              />
            </div>
          ))
        ) : (
          <div className="min-w-0 flex-1 overflow-hidden rounded-2xl border border-white/10">
            <img
              src={template.images[0]}
              alt={template.title}
              className="size-full object-cover"
            />
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 px-2 py-1">
        <GradientBadge as={template.icon} seed={template.id} />
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="truncate text-sm font-medium text-foreground">
            {template.title}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            {template.subtitle}
          </span>
        </div>
        <Button
          size="sm"
          className="rounded-full font-semibold"
          onClick={(event) => {
            event.stopPropagation()
            onTry(template)
          }}
        >
          {tryLabel}
        </Button>
      </div>
    </div>
  )
}

export interface ExamplePresetsProps {
  items: TemplateItem[]
  onUse: (template: TemplateItem) => void
  tryLabel?: ReactNode
  className?: string
}

/** The Explore grid: two columns of `TemplateCard`s. */
export function ExamplePresets({
  items,
  onUse,
  tryLabel = "Try",
  className = "w-full max-w-[900px]",
}: ExamplePresetsProps) {
  return (
    <div
      className={cn("grid w-full grid-cols-1 gap-5 sm:grid-cols-2", className)}
    >
      {items.map((t) => (
        <TemplateCard
          key={t.id}
          template={t}
          onTry={onUse}
          tryLabel={tryLabel}
        />
      ))}
    </div>
  )
}
