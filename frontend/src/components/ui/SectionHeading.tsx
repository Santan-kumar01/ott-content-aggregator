import React from "react";
import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  badge?: string;
  badgeIcon?: React.ReactNode;
  title: string;
  highlight?: string;
  description?: string;
  centered?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function SectionHeading({
  badge,
  badgeIcon,
  title,
  highlight,
  description,
  centered = true,
  className,
  children,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "space-y-3",
        centered ? "text-center max-w-2xl mx-auto" : "max-w-xl",
        className
      )}
    >
      {badge && (
        <div
          className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider",
            "border border-white/10 bg-white/5 text-purple-300/90 backdrop-blur-md shadow-inner shadow-purple-500/10",
            centered && "mx-auto"
          )}
        >
          {badgeIcon}
          <span>{badge}</span>
        </div>
      )}

      <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white leading-tight">
        {title}{" "}
        {highlight && (
          <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-300 bg-clip-text text-transparent">
            {highlight}
          </span>
        )}
      </h2>

      {description && (
        <p className="text-sm sm:text-base text-zinc-400 leading-relaxed">
          {description}
        </p>
      )}

      {children}
    </div>
  );
}

