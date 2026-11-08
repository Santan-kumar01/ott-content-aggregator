"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic,
  Square,
  Sparkles,
  X,
  RotateCcw,
  AlertCircle,
  Loader2,
  Film,
  Tv,
  ArrowRight,
  Tag,
  Calendar,
  Radio,
} from "lucide-react";
import { voiceService } from "@/lib/services/voice";
import type { VoiceSearchResponse, ParsedVoiceQuery } from "@/types";

interface VoiceSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyResults?: (query: string, parsed: ParsedVoiceQuery) => void;
}

type VoiceState = "idle" | "recording" | "processing" | "results" | "error";

const EXAMPLE_QUERIES = [
  "Sci-Fi movies on Prime",
  "Breaking Bad or Stranger Things",
  "Christopher Nolan directed films",
  "Drama series from 2022 on Netflix",
];

export function VoiceSearchModal({
  isOpen,
  onClose,
  onApplyResults,
}: VoiceSearchModalProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [recordingDuration, setRecordingDuration] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [response, setResponse] = useState<VoiceSearchResponse | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Stop recording & release media hardware
  const cleanupMediaStream = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
      mediaStreamRef.current = null;
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  }, []);

  // Handle modal close with full cleanup
  const handleClose = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    cleanupMediaStream();
    setState("idle");
    setRecordingDuration(0);
    setErrorMessage(null);
    setResponse(null);
    onClose();
  }, [cleanupMediaStream, onClose]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose]);

  // Clean up when unmounting
  useEffect(() => {
    return () => {
      cleanupMediaStream();
    };
  }, [cleanupMediaStream]);

  // Start recording
  const startRecording = async () => {
    setErrorMessage(null);
    setResponse(null);
    audioChunksRef.current = [];

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setState("error");
      setErrorMessage("Microphone audio capture is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      // Select supported mimeType
      let mimeType = "audio/webm;codecs=opus";
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
          mimeType = "audio/ogg;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
          mimeType = "audio/ogg";
        } else {
          mimeType = ""; // Browser default
        }
      }

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        cleanupMediaStream();

        const recordedBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        if (recordedBlob.size === 0) {
          setState("error");
          setErrorMessage("No audio was recorded. Please try again.");
          return;
        }

        setState("processing");

        try {
          const result = await voiceService.searchByVoice(recordedBlob);
          setResponse(result);
          setState("results");
        } catch (err) {
          setState("error");
          setErrorMessage(
            err instanceof Error
              ? err.message
              : "Voice search encountered an unexpected error."
          );
        }
      };

      recorder.start(250); // Slice every 250ms
      setState("recording");
      setRecordingDuration(0);

      timerIntervalRef.current = setInterval(() => {
        setRecordingDuration((prev) => {
          if (prev >= 25) {
            // Auto stop after 25 seconds
            stopRecording();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      cleanupMediaStream();
      setState("error");
      if ((err as Error).name === "NotAllowedError" || (err as Error).name === "PermissionDeniedError") {
        setErrorMessage("Microphone access was denied. Please allow microphone permissions in your browser.");
      } else {
        setErrorMessage("Could not initialize microphone: " + (err as Error).message);
      }
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  };

  // Apply parsed query to Discover page
  const handleApply = () => {
    if (!response) return;
    const { parsed_query, transcription } = response;
    const query = parsed_query.cleaned_query || parsed_query.search_query || transcription;
    if (onApplyResults) {
      onApplyResults(query, parsed_query);
    }
    handleClose();
  };

  if (!isOpen) return null;

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Voice Search"
    >
      {/* Click outside backdrop */}
      <div className="absolute inset-0" onClick={handleClose} />

      {/* Modal Container */}
      <div className="relative w-full max-w-lg rounded-2xl bg-zinc-900 border border-white/10 p-6 sm:p-8 shadow-2xl shadow-purple-950/40 z-10 overflow-hidden">
        {/* Glow behind modal */}
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-64 h-32 bg-purple-500/20 blur-3xl pointer-events-none rounded-full" />

        {/* Close Button */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          aria-label="Close voice search"
        >
          <X className="size-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-6">
          <div className="p-2 rounded-xl bg-purple-600/20 border border-purple-500/30 text-purple-400">
            <Mic className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              Voice Assisted Search
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                AI Powered
              </span>
            </h2>
            <p className="text-xs text-zinc-400">
              Speak naturally in any phrasing — AI extracts title, genres, and platforms
            </p>
          </div>
        </div>

        {/* Content Area Based on State */}
        <div className="py-2">
          {/* STATE: IDLE */}
          {state === "idle" && (
            <div className="flex flex-col items-center text-center py-6">
              <button
                type="button"
                onClick={startRecording}
                className="relative group p-6 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-600 text-white shadow-xl shadow-purple-600/40 hover:scale-105 active:scale-95 transition-all cursor-pointer"
                aria-label="Start recording"
              >
                <div className="absolute inset-0 rounded-full bg-purple-500 animate-ping opacity-25 group-hover:opacity-40" />
                <Mic className="size-10 relative z-10" />
              </button>

              <p className="mt-5 text-sm font-semibold text-white">
                Tap the microphone to speak
              </p>
              <p className="text-xs text-zinc-400 mt-1 max-w-xs">
                Describe what you want to watch by title, genre, year, or streaming platform.
              </p>

              {/* Suggestions */}
              <div className="mt-6 w-full pt-4 border-t border-white/5">
                <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-2.5">
                  Try asking things like:
                </p>
                <div className="flex flex-wrap gap-1.5 justify-center">
                  {EXAMPLE_QUERIES.map((example) => (
                    <span
                      key={example}
                      className="text-xs px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-zinc-300"
                    >
                      &ldquo;{example}&rdquo;
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STATE: RECORDING */}
          {state === "recording" && (
            <div className="flex flex-col items-center text-center py-6">
              <div className="relative">
                {/* Sound wave rings */}
                <div className="absolute inset-0 -m-3 rounded-full border-2 border-purple-500/40 animate-ping" />
                <div className="absolute inset-0 -m-6 rounded-full border border-purple-500/20 animate-pulse" />

                <button
                  type="button"
                  onClick={stopRecording}
                  className="relative p-6 rounded-full bg-red-600 hover:bg-red-500 text-white shadow-xl shadow-red-600/40 transition-all cursor-pointer"
                  aria-label="Stop recording"
                >
                  <Square className="size-8 fill-current" />
                </button>
              </div>

              {/* Timer & Listening Indicator */}
              <div className="mt-6 flex items-center gap-2 text-red-400 text-sm font-mono font-bold">
                <span className="size-2 rounded-full bg-red-500 animate-pulse" />
                <span>Listening ({formatSeconds(recordingDuration)})</span>
              </div>

              <p className="text-xs text-zinc-400 mt-2">
                Tap the red button when you&apos;re done speaking
              </p>
            </div>
          )}

          {/* STATE: PROCESSING */}
          {state === "processing" && (
            <div className="flex flex-col items-center text-center py-8">
              <div className="relative p-6 rounded-full bg-purple-600/20 border border-purple-500/30 text-purple-400">
                <Loader2 className="size-10 animate-spin" />
              </div>
              <p className="mt-5 text-sm font-semibold text-white">
                Transcribing & analyzing speech...
              </p>
              <p className="text-xs text-zinc-400 mt-1 max-w-xs">
                Groq AI is transcribing audio and extracting catalogue search parameters.
              </p>
            </div>
          )}

          {/* STATE: RESULTS */}
          {state === "results" && response && (
            <div className="space-y-4">
              {/* Transcribed query card */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <span className="text-[10px] font-mono uppercase tracking-wider text-purple-400 block mb-1">
                  Transcribed Audio
                </span>
                <p className="text-sm sm:text-base font-semibold text-white italic">
                  &ldquo;{response.transcription}&rdquo;
                </p>
              </div>

              {/* Parsed attributes */}
              <div className="p-3.5 rounded-xl bg-purple-950/30 border border-purple-500/20">
                <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block mb-2">
                  Deterministic Entity Extraction
                </span>

                <div className="flex flex-wrap gap-2">
                  {/* Intent */}
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30 font-medium">
                    <Sparkles className="size-3" />
                    <span>Intent: {response.parsed_query.intent}</span>
                  </span>

                  {/* Cleaned query */}
                  {response.parsed_query.cleaned_query && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-white/5 text-zinc-300 border border-white/10 font-medium">
                      <Tag className="size-3 text-zinc-400" />
                      <span>Query: &ldquo;{response.parsed_query.cleaned_query}&rdquo;</span>
                    </span>
                  )}

                  {/* Genre */}
                  {response.parsed_query.genre && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-medium">
                      <span>Genre: {response.parsed_query.genre}</span>
                    </span>
                  )}

                  {/* Platform */}
                  {response.parsed_query.platform && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium">
                      <Radio className="size-3 text-emerald-400" />
                      <span>Platform: {response.parsed_query.platform}</span>
                    </span>
                  )}

                  {/* Release Year */}
                  {response.parsed_query.release_year && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
                      <Calendar className="size-3 text-amber-400" />
                      <span>Year: {response.parsed_query.release_year}</span>
                    </span>
                  )}

                  {/* Content Type */}
                  {response.parsed_query.content_type && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 font-medium">
                      {response.parsed_query.content_type === "movie" ? (
                        <Film className="size-3" />
                      ) : (
                        <Tv className="size-3" />
                      )}
                      <span className="capitalize">{response.parsed_query.content_type}</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Matched Titles Preview */}
              <div>
                <div className="flex items-center justify-between text-xs text-zinc-400 mb-2">
                  <span>Matched Titles ({response.count} found)</span>
                </div>

                {response.titles && response.titles.length > 0 ? (
                  <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                    {response.titles.slice(0, 4).map((title) => (
                      <div
                        key={title.id}
                        className="p-2.5 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between text-xs"
                      >
                        <div className="min-w-0 pr-2">
                          <p className="font-semibold text-white truncate">{title.name}</p>
                          <p className="text-[11px] text-zinc-400">
                            {title.release_year} • {title.genre}
                          </p>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30 shrink-0">
                          {title.platform}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 italic py-2">
                    No immediate exact matches found for this voice query in the current catalog.
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center gap-2">
                <button
                  type="button"
                  onClick={startRecording}
                  className="flex-1 py-2.5 px-3 rounded-xl text-xs font-semibold text-zinc-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <RotateCcw className="size-3.5" />
                  <span>Speak Again</span>
                </button>

                <button
                  type="button"
                  onClick={handleApply}
                  className="flex-1 py-2.5 px-3 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-md shadow-purple-600/30 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <span>Apply to Discover</span>
                  <ArrowRight className="size-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STATE: ERROR */}
          {state === "error" && (
            <div className="flex flex-col items-center text-center py-6">
              <div className="p-3.5 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 mb-3">
                <AlertCircle className="size-8" />
              </div>

              <h3 className="text-sm font-semibold text-white">Voice Search Notice</h3>
              <p className="text-xs text-zinc-400 mt-1.5 max-w-xs leading-relaxed">
                {errorMessage || "An error occurred while processing voice input."}
              </p>

              <div className="mt-5 flex items-center gap-2">
                <button
                  type="button"
                  onClick={startRecording}
                  className="py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <RotateCcw className="size-3.5" />
                  <span>Try Again</span>
                </button>
                <button
                  type="button"
                  onClick={handleClose}
                  className="py-2.5 px-4 rounded-xl text-xs font-semibold text-zinc-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

