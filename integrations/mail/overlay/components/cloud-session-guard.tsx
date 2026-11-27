'use client';
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { DESK, logoutEpoch, markRemoteCleanup } from '@/lib/cloud-session';
export function CloudSessionGuard() {
  useEffect(() => {
    const initial = logoutEpoch(); let busy = false;
    const check = () => {
      if (busy || initial === logoutEpoch() || !useAuthStore.getState().isAuthenticated) return;
      busy = true; markRemoteCleanup();
      // Preserve drafts/offline data while revoking every authenticated account slot.
      void useAuthStore.getState().logoutAll({endProviderSession:false,keepLocalData:true});
    };
    const timer = window.setInterval(check, 500);
    window.addEventListener('focus', check); window.addEventListener('pageshow', check);
    return () => { clearInterval(timer); window.removeEventListener('focus', check); window.removeEventListener('pageshow', check); };
  }, []);
  // P53: sign-out lives on the Desk. Inside the Desk every sign-out control of this app is hidden and the
  // Desk's two questions are answered; opened on its own, the control becomes the way back to the Desk.
  useEffect(() => {
    const framed = window.self !== window.top; let queued = false;
    const own = (el: Element) => /^(sign out( of .+)?|log ?out)$/i.test((el.textContent || '').trim());
    const sweep = () => {
      queued = false;
      for (const el of Array.from(document.querySelectorAll<HTMLElement>('button,[role="menuitem"],[role="option"]'))) {
        if (el.dataset.cloudDesk || !own(el)) continue;
        el.dataset.cloudDesk = '1';
        if (framed) { el.style.display = 'none'; continue; }
        const text = Array.from(el.querySelectorAll('*')).reverse().find(n => !n.children.length && !n.closest('svg') && (n.textContent || '').trim());
        (text || el).textContent = 'Back to home';
        el.addEventListener('click', e => { e.preventDefault(); e.stopImmediatePropagation(); window.location.assign(DESK + '/'); }, true);
      }
    };
    const observer = new MutationObserver(() => { if (!queued) { queued = true; window.setTimeout(sweep, 150); } });
    observer.observe(document.body, { childList: true, subtree: true }); sweep();
    const onMessage = (e: MessageEvent) => {
      if (!framed || e.origin !== DESK || e.source !== window.parent || e.data?.source !== 'cloud-desk') return;
      if (e.data.type === 'unsaved?') {
        window.parent.postMessage({ source: 'cloud-session', type: 'unsaved', value: !!document.querySelector('[data-testid="email-composer"]') }, DESK);
      } else if (e.data.type === 'signout') {
        if (useAuthStore.getState().isAuthenticated) void useAuthStore.getState().logoutAll();
        else window.parent.postMessage({ source: 'cloud-session', type: 'logout' }, DESK);
      }
    };
    window.addEventListener('message', onMessage);
    return () => { observer.disconnect(); window.removeEventListener('message', onMessage); };
  }, []);
  return null;
}
