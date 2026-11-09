"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Mic,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Database,
  Radio,
} from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { cn } from "@/lib/utils";

const SAMPLE_VOICE_QUERIES = [
  {
    speech: "Show me 90s action movies on Prime",
    intent: "filter",
    extracted: {
      genre: "Action",
      platform: "Prime Video",
      release_year: "1990-1999",
      content_type: "Movie",
    },
    sampleMatches: ["Terminator 2: Judgment Day", "Speed", "The Matrix"],
  },
  {
    speech: "Find Christopher Nolan sci-fi movies on Netflix",
    intent: "search",
    extracted: {
      genre: "Sci-Fi",
      platform: "Netflix",
      director: "Christopher Nolan",
      content_type: "Movie",
    },
    sampleMatches: ["Inception", "Interstellar"],
  },
  {
    speech: "Recommend mind-bending mystery series on Apple TV+",
    intent: "filter",
    extracted: {
      genre: "Mystery / Thriller",
      platform: "Apple TV+",
      content_type: "Show",
    },
    sampleMatches: ["Severance", "Silo", "Defending Jacob"],
  },
];

export function VoiceDemoSection({ className }: { className?: string }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const currentDemo = SAMPLE_VOICE_QUERIES[selectedIdx];

  return (
    <section
      id="voice-search"
      className={cn("py-20 sm:py-28 relative overflow-hidden", className)}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <SectionHeading
          badge="AI VOICE ASSISTANT"
          badgeIcon={<Mic className="size-3.5 text-purple-400" />}
          title="Speak Naturally."
          highlight="Find Anything Instantly."
          description="Powered by Groq Whisper and real-time NLP intent extraction. Discover content just by describing what you want to watch."
          centered
        />

        {/* Demo Switcher Tabs */}
        <div className="mt-10 flex flex-wrap justify-center gap-2">
          {SAMPLE_VOICE_QUERIES.map((demo, idx) => (
            <button
              key={demo.speech}
              type="button"
              onClick={() => setSelectedIdx(idx)}
              className={cn(
                "px-4 py-2 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer flex items-center gap-2",
                selectedIdx === idx
                  ? "bg-purple-600 text-white shadow-lg shadow-purple-600/30 border border-purple-400/40"
                  : "bg-zinc-900/80 text-zinc-400 hover:text-white border border-white/10 hover:border-white/20"
              )}
            >
              <Mic className="size-3 text-purple-300" />
              <span>Prompt {idx + 1}</span>
            </button>
          ))}
        </div>

        {/* Voice Pipeline Interactive Visualization */}
        <div className="mt-10 max-w-4xl mx-auto p-6 sm:p-8 rounded-3xl bg-zinc-950/80 border border-white/10 backdrop-blur-2xl shadow-2xl shadow-purple-950/40">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 items-stretch">
            {/* Stage 1: Audio Input */}
            <div className="flex flex-col justify-between p-5 rounded-2xl bg-zinc-900/60 border border-white/10">
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-4">
                  <span className="flex items-center gap-1.5 text-purple-400">
                    <Radio className="size-3.5 animate-pulse" /> 01. AUDIO INPUT
                  </span>
                  <span className="text-[10px] uppercase text-zinc-500">Live</span>
                </div>

                <div className="relative py-4 flex flex-col items-center justify-center">
                  <div className="relative p-4 rounded-full bg-purple-600/20 border border-purple-500/40 mb-3 shadow-lg shadow-purple-600/30">
                    <Mic className="size-6 text-purple-300" />
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-purple-500"></span>
                    </span>
                  </div>

                  <p className="text-xs sm:text-sm font-medium text-white text-center italic">
                    &ldquo;{currentDemo.speech}&rdquo;
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 text-[11px] text-zinc-500 font-mono text-center">
                Groq Whisper v3 Large
              </div>
            </div>

            {/* Stage 2: NLP Intent Extraction */}
            <div className="flex flex-col justify-between p-5 rounded-2xl bg-zinc-900/60 border border-white/10">
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-4">
                  <span className="flex items-center gap-1.5 text-pink-400">
                    <Cpu className="size-3.5" /> 02. INTENT PARSER
                  </span>
                  <span className="text-[10px] uppercase text-zinc-500">FastAPI</span>
                </div>

                <div className="space-y-2 text-xs font-mono">
                  <div className="p-2 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
                    <span className="text-zinc-500">intent:</span>
                    <span className="text-emerald-400 font-bold uppercase">
                      {currentDemo.intent}
                    </span>
                  </div>

                  {Object.entries(currentDemo.extracted).map(([key, val]) => (
                    <div
                      key={key}
                      className="p-1.5 px-2 rounded-lg bg-black/30 border border-white/5 flex items-center justify-between"
                    >
                      <span className="text-zinc-500">{key}:</span>
                      <span className="text-purple-300 font-medium">{val}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 text-[11px] text-zinc-500 font-mono text-center">
                Sub-20ms NLP Extraction
              </div>
            </div>

            {/* Stage 3: Catalog Matches */}
            <div className="flex flex-col justify-between p-5 rounded-2xl bg-zinc-900/60 border border-white/10">
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-4">
                  <span className="flex items-center gap-1.5 text-cyan-400">
                    <Database className="size-3.5" /> 03. FILTERED MATCHES
                  </span>
                  <span className="text-[10px] uppercase text-zinc-500">Redis</span>
                </div>

                <div className="space-y-2">
                  {currentDemo.sampleMatches.map((title) => (
                    <div
                      key={title}
                      className="p-2.5 rounded-xl bg-purple-950/20 border border-purple-500/20 flex items-center gap-2"
                    >
                      <CheckCircle2 className="size-3.5 text-purple-400 shrink-0" />
                      <span className="text-xs font-medium text-white truncate">
                        {title}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 text-[11px] text-zinc-500 font-mono text-center">
                Instant Paginated Titles
              </div>
            </div>
          </div>

          {/* Action Callout */}
          <div className="mt-8 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs sm:text-sm text-zinc-400">
              <Sparkles className="size-4 text-purple-400" />
              <span>Full microphone integration in the Discover Catalog.</span>
            </div>

            <Link
              href="/discover?voice=true"
              className={cn(
                "inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold",
                "bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all",
                "cursor-pointer active:scale-95"
              )}
            >
              <Mic className="size-3.5" />
              <span>Try Live Voice Search</span>
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

