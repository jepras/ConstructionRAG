// frontend/src/lib/constants.ts
/**
 * Constants for unified storage migration
 */

// Anonymous user constants for unified storage pattern
export const ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000";
export const ANONYMOUS_USERNAME = "anonymous";

// Visibility levels for unified access control
export const VisibilityLevel = {
  PUBLIC: "public",
  PRIVATE: "private",
  INTERNAL: "internal"
} as const;

export type VisibilityLevel = typeof VisibilityLevel[keyof typeof VisibilityLevel];

// Valid visibility levels array
export const VALID_VISIBILITY_LEVELS = Object.values(VisibilityLevel);