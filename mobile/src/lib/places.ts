// The header's project / site / shift (owner, 23 November 2026: each sub-location is a Field Site of a Project;
// the header lists the projects the person has a site in, and the sites under the chosen project). Built only
// from what custom_hr's bootstrap returns for the person; the choice is a phone-only preference.
import * as SecureStore from 'expo-secure-store';
import { useSyncExternalStore } from 'react';

export { type Place, type Shift, placesFrom, projectsOf, resolvePlace } from '@/lib/attendance';

export type Choice = { site: string | null; shift: string | null };
const KEY = 'header-place';
let choice: Choice = { site: null, shift: null };
let loaded = false;
const listeners = new Set<() => void>();
const set = (next: Choice) => {
  choice = next;
  listeners.forEach((l) => l());
  SecureStore.setItemAsync(KEY, JSON.stringify(next)).catch(() => {});
};

/** Choose a site (its current shift is chosen with it) or a shift of the chosen site. */
export const choosePlace = (site: string, shift: string | null) => set({ site, shift });

/** The remembered choice, read once per app start. */
export async function loadPlaceChoice() {
  if (loaded) return;
  loaded = true;
  try {
    const saved = JSON.parse((await SecureStore.getItemAsync(KEY)) ?? 'null') as Choice | null;
    if (saved?.site) {
      choice = { site: saved.site, shift: saved.shift ?? null };
      listeners.forEach((l) => l());
    }
  } catch {
    // no saved choice
  }
}

const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => listeners.delete(l);
};
export const usePlaceChoice = () => useSyncExternalStore(subscribe, () => choice);
