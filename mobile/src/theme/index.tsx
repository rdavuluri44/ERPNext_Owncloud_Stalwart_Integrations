import * as SecureStore from 'expo-secure-store';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useWindowDimensions } from 'react-native';

import { palette, type PaletteColor } from './colors';

type Theme = {
  c: Record<PaletteColor, string>;
  outdoor: boolean;
  setOutdoor: (on: boolean) => void;
  /** Scales a font size; Outdoor mode makes everything 20% larger. */
  font: (size: number) => number;
  /** Minimum touch target height (48 dp normal, 56 dp Outdoor: glove-friendly). */
  touch: number;
  border: number;
};

const ThemeContext = createContext<Theme | null>(null);

const OUTDOOR_KEY = 'outdoor-mode';

/** Outdoor mode is a phone-only preference (build guide section 7): it stays on after the app restarts. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [outdoor, setOutdoorState] = useState(false);
  useEffect(() => {
    SecureStore.getItemAsync(OUTDOOR_KEY).then(
      (saved) => saved === '1' && setOutdoorState(true),
      () => {},
    );
  }, []);
  const setOutdoor = (on: boolean) => {
    setOutdoorState(on);
    SecureStore.setItemAsync(OUTDOOR_KEY, on ? '1' : '0').catch(() => {});
  };
  const theme: Theme = {
    // Outdoor (sunlight): white surfaces, near-black outlines, strong row lines.
    c: outdoor ? { ...palette, surface: palette.bg, border: '#1F1F1F', divider: palette.line } : palette,
    outdoor,
    setOutdoor,
    font: (size) => Math.round(size * (outdoor ? 1.2 : 1)),
    touch: outdoor ? 56 : 48,
    border: outdoor ? 3 : 1,
  };
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error('useTheme must be used inside ThemeProvider');
  return theme;
}

/** Tablets (and big phones in landscape) get a split view: list on the left, detail on the right. */
export function useIsTablet(): boolean {
  return useWindowDimensions().width >= 768;
}

/** Build guide: from 600 dp (tablets, phones in landscape) the tabs become a side rail. */
export function useSideRail(): boolean {
  return useWindowDimensions().width >= 600;
}
