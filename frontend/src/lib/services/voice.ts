/**
 * OTT Content Aggregator - Voice Search Service
 *
 * Interfaces with FastAPI backend voice endpoints:
 * - POST /api/v1/voice/search?skip=0&limit=10 (multipart/form-data with file)
 * - POST /api/v1/voice/transcribe (multipart/form-data with file)
 *
 * Supports WebM, WAV, OGG audio blobs recorded by browser MediaRecorder.
 */

import { api, ApiError } from "@/lib/api";
import type { VoiceSearchResponse } from "@/types";

export interface VoiceSearchOptions {
  skip?: number;
  limit?: number;
  timeoutMs?: number;
}

export const voiceService = {
  /**
   * Send recorded audio blob to backend voice search endpoint.
   * Transcribes speech, deterministically extracts intent/entities, and queries catalog.
   */
  async searchByVoice(
    audioBlob: Blob,
    options: VoiceSearchOptions = {}
  ): Promise<VoiceSearchResponse> {
    const { skip = 0, limit = 12, timeoutMs = 25000 } = options;

    if (!audioBlob || audioBlob.size === 0) {
      throw new Error("No audio was recorded. Please try speaking again.");
    }

    if (audioBlob.size > 10 * 1024 * 1024) {
      throw new Error("Audio recording exceeds the 10 MB maximum limit.");
    }

    // Determine appropriate extension from blob mimeType
    let extension = "webm";
    if (audioBlob.type.includes("ogg")) {
      extension = "ogg";
    } else if (audioBlob.type.includes("wav")) {
      extension = "wav";
    } else if (audioBlob.type.includes("mp4") || audioBlob.type.includes("m4a")) {
      extension = "m4a";
    }

    const formData = new FormData();
    formData.append("file", audioBlob, `voice_query.${extension}`);

    try {
      return await api.post<VoiceSearchResponse>(
        `/api/v1/voice/search?skip=${skip}&limit=${limit}`,
        formData,
        { timeoutMs }
      );
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 503) {
          throw new Error(
            "Voice transcription is unavailable because GROQ_API_KEY is not configured on the server."
          );
        }
        if (error.status === 400) {
          throw new Error(
            error.message || "Invalid audio format. Please ensure microphone access and speak clearly."
          );
        }
        if (error.status === 413) {
          throw new Error("Recorded audio is too large. Please record a shorter query.");
        }
        if (error.status === 429) {
          throw new Error("Voice search rate limit reached. Please wait a moment and try again.");
        }
        if (error.status === 502 || error.status === 504) {
          throw new Error("Voice transcription provider service error. Please try again.");
        }
        throw new Error(error.message || "Failed to process voice query.");
      }
      throw new Error("Unable to connect to voice search server. Please ensure the backend is running.");
    }
  },

  /**
   * Transcribe recorded audio blob without running catalog search.
   */
  async transcribe(audioBlob: Blob): Promise<string> {
    const formData = new FormData();
    const extension = audioBlob.type.includes("ogg") ? "ogg" : "webm";
    formData.append("file", audioBlob, `speech.${extension}`);

    try {
      const result = await api.post<{ text: string }>(
        "/api/v1/voice/transcribe",
        formData,
        { timeoutMs: 25000 }
      );
      return result.text;
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 503) {
          throw new Error("Voice transcription service configuration is missing on the server.");
        }
        throw new Error(error.message || "Speech transcription failed.");
      }
      throw new Error("Unable to reach transcription server.");
    }
  },
};

