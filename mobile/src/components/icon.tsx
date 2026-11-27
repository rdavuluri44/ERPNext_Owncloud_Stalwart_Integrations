// The app's icons: outlined vector icons (Lucide, ISC licence), 24 dp on a 2 px stroke, never emoji or text
// symbols (owner's design brief, 23 November 2026). One fixed list, so a wrong name is a type error.
import {
  ArrowLeft,
  Bell,
  Building,
  CalendarDays,
  CalendarHeart,
  Camera,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  CircleCheck,
  CircleUserRound,
  CircleX,
  ClipboardCheck,
  Clock3,
  CloudOff,
  CloudUpload,
  FingerprintPattern,
  Hand,
  Image,
  Inbox,
  Info,
  LocateFixed,
  LogOut,
  type LucideIcon,
  MapPin,
  MapPinCheck,
  MapPinX,
  Menu,
  Moon,
  OctagonX,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  ScanFace,
  Search,
  Square,
  SquareCheck,
  Sun,
  TriangleExclamationPoint,
  Undo2,
  Users,
  X,
} from 'lucide-react-native';

const ICONS = {
  back: ArrowLeft,
  bell: Bell,
  site: Building,
  today: CalendarDays,
  holiday: CalendarHeart,
  camera: Camera,
  check: Check,
  'chevron-down': ChevronDown,
  'chevron-right': ChevronRight,
  'chevron-up': ChevronUp,
  ok: CircleCheck,
  person: CircleUserRound,
  clear: CircleX,
  approve: ClipboardCheck,
  pending: Clock3,
  offline: CloudOff,
  upload: CloudUpload,
  fingerprint: FingerprintPattern,
  hand: Hand,
  image: Image,
  inbox: Inbox,
  info: Info,
  locate: LocateFixed,
  'sign-out': LogOut,
  'map-pin': MapPin,
  'checked-in': MapPinCheck,
  'not-checked-in': MapPinX,
  menu: Menu,
  night: Moon,
  danger: OctagonX,
  plus: Plus,
  refresh: RefreshCw,
  retake: RotateCcw,
  save: Save,
  face: ScanFace,
  search: Search,
  'box-empty': Square,
  'box-checked': SquareCheck,
  sun: Sun,
  warn: TriangleExclamationPoint,
  undo: Undo2,
  team: Users,
  close: X,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof ICONS;

/** An outlined icon, 24 dp with a 2 px stroke by default; decorative unless it is the only label. */
export function Icon({ name, size = 24, color, label }: { name: IconName; size?: number; color: string; label?: string }) {
  const Glyph = ICONS[name];
  return (
    <Glyph
      size={size}
      color={color}
      strokeWidth={2}
      absoluteStrokeWidth
      accessibilityLabel={label}
      accessible={!!label}
      importantForAccessibility={label ? 'yes' : 'no-hide-descendants'}
    />
  );
}
