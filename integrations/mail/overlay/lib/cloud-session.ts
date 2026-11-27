const FINISH = 'https://erp.example.com/api/method/erpnext_drive_integrations.portal.sso.finish_logout';
const SIGNED_OUT = 'https://erp.example.com/login?logged_out=1';
/** P53: the Desk (portal page) that frames this app and holds the one sign-out. */
export const DESK = 'https://erp.example.com';
let remoteCleanup = false;
export function logoutEpoch(): string {
  return typeof document === 'undefined' ? '' : document.cookie.split(';').find(v => v.trim().startsWith('cloud_logout_epoch='))?.trim() || '';
}
export function markRemoteCleanup(): void { remoteCleanup = true; }
export function finishWorkspaceLogout(userInitiated: boolean): boolean {
  if (typeof window === 'undefined') return false;
  if (remoteCleanup || !userInitiated) {
    if (remoteCleanup) window.location.replace(SIGNED_OUT);
    return remoteCleanup;
  }
  const epoch = crypto.randomUUID();
  document.cookie = `cloud_logout_epoch=${epoch}; Domain=example.com; Path=/; Secure; SameSite=Lax; Max-Age=604800`;
  if (window.self !== window.top) {
    window.parent.postMessage({ source: 'cloud-session', type: 'logout' }, 'https://erp.example.com');
  } else window.location.replace(FINISH);
  return true;
}
