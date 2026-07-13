// SECTION: IMPORTS
// Description: Imports utilities for styling class formatting and Tailwind CSS conflicts resolution.

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"


// SECTION: CLASS NAMES MERGER UTILITY
// Description: Merges various styling classes arrays, filters falsey flags, and resolves active conflicts.

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
