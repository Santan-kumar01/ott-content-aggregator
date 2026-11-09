import React from "react";
import {
  Layers,
  Mic,
  Zap,
  SlidersHorizontal,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { cn } from "@/lib/utils";

interface FeatureItem {
  icon: React.ReactNode;
  badge: string;
  title: string;
  description: string;
  highlightText: string;
}

const FEATURES: FeatureItem[] = [
  {
    icon: <Layers className="size-6 text-purple-400" />,
    badge: "UNIFIED ECOSYSTEM",
    title: "One Search Across Every Service",
    description:
      "Stop juggling multiple apps and search bars. Our catalog combines Netflix, Prime Video, Disney+, Max, Apple TV+, and more into a single high-performance dashboard.",
    highlightText: "Zero app switching",
  },
  {
    icon: <Mic className="size-6 text-pink-400" />,
    badge: "VOICE INTELLIGENCE",
    title: "Natural Voice Search via Groq Whisper",
    description:
      "Speak the way you think. Our AI speech pipeline transcribes your voice, extracts genre, platform, and year intents, and delivers instant curated recommendations.",
    highlightText: "Sub-second NLP pipeline",
  },
  {
    icon: <Zap className="size-6 text-amber-400" />,
    badge: "INSTANT DISCOVERY",
    title: "Sub-Millisecond Redis Caching",
    description:
      "Experience frictionless catalog browsing. Automated cache invalidation and tiered memory caching deliver responses with zero perceptible latency.",
    highlightText: "Sub-10ms query speeds",
  },
  {
    icon: <SlidersHorizontal className="size-6 text-cyan-400" />,
    badge: "PRECISION FILTERING",
    title: "Multi-Parametric Catalog Filters",
    description:
      "Slice through 10,000+ titles with granular filtering by content type, release year, streaming provider, genre, and verified viewer ratings.",
    highlightText: "100% verified metadata",
  },
];

export function FeaturesSection({ className }: { className?: string }) {
  return (
    <section
      id="features"
      className={cn(
        "py-20 sm:py-28 relative overflow-hidden bg-zinc-950/40 border-y border-white/5",
        className
      )}
    >
      {/* Background ambient decorative gradients */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-80 h-80 rounded-full bg-purple-600/10 blur-[100px] pointer-events-none" />
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-80 h-80 rounded-full bg-indigo-600/10 blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <SectionHeading
          badge="WHY USE OUR AGGREGATOR"
          badgeIcon={<ShieldCheck className="size-3.5 text-purple-400" />}
          title="Engineered for"
          highlight="Effortless Entertainment"
          description="A complete architectural rethink of how you find entertainment. Faster, smarter, and always connected to what you want to watch."
          centered
        />

        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className={cn(
                "group relative p-6 sm:p-8 rounded-3xl",
                "bg-zinc-950/70 border border-white/10 backdrop-blur-xl",
                "hover:border-purple-500/40 hover:shadow-2xl hover:shadow-purple-950/30",
                "transition-all duration-300 ease-out flex flex-col justify-between"
              )}
            >
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md group-hover:scale-110 transition-transform">
                    {feature.icon}
                  </div>
                  <span className="px-3 py-1 rounded-full text-[10px] font-mono font-bold tracking-wider uppercase bg-white/5 border border-white/10 text-zinc-400">
                    {feature.badge}
                  </span>
                </div>

                <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight group-hover:text-purple-300 transition-colors">
                  {feature.title}
                </h3>

                <p className="mt-3 text-sm sm:text-base text-zinc-400 leading-relaxed">
                  {feature.description}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-white/5 flex items-center gap-2 text-xs font-semibold text-purple-400">
                <CheckCircle2 className="size-4 shrink-0" />
                <span>{feature.highlightText}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

