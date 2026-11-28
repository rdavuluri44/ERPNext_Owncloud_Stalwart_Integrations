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
      } else if (e.data.type === 'look' && [0.9, 1, 1.15].includes(e.data.font)) {
        // P111: the font size chosen in the Desk's bar.
        document.documentElement.style.setProperty('zoom', String(e.data.font));
      }
    };
    window.addEventListener('message', onMessage);
    return () => { observer.disconnect(); window.removeEventListener('message', onMessage); };
  }, []);
  // P116: inside the Desk, Mail has one left pane. The narrow first pane is not drawn as a pane: its five
  // entries (mail, calendar, contacts, settings, add) sit as one row beneath the account name; its notification,
  // keyboard-shortcut and account buttons are hidden (the Desk's bar has notifications and the person's menu;
  // the shortcuts themselves keep working). The folder pane cannot be folded. On pages without a folder pane
  // (calendar, contacts, settings) the row lies across the top. Wide screens only: on a phone the webmail
  // keeps its own layout.
  useEffect(() => {
    if (window.self === window.top) return;
    const css = document.createElement('style'); css.id = 'cloud-mail-desk';
    css.textContent = '@media(min-width:1024px){' +
      '.uf-rail{width:0!important;min-width:0!important;flex:none!important;overflow:visible!important;position:static!important;background:transparent!important}' +
      '.uf-rail-inner{position:absolute!important;z-index:51;left:0;top:var(--uf-lane-top,56px);width:var(--uf-lane-width,256px);height:44px!important;' +
      'display:flex!important;flex-direction:row!important;align-items:center!important;justify-content:space-around!important;padding:0 8px!important;overflow:visible!important;box-sizing:border-box}' +
      '.uf-rail-inner>nav,.uf-rail-inner>div{display:contents!important}' +
      '.uf-rail-inner .uf-lane-hide{display:none!important}' +
      '.uf-rail-inner [class*="h-px"],.uf-rail-inner [role=separator],.uf-rail-inner hr{display:none!important}' +
      '.uf-rail-inner .uf-lane-settings{order:4}.uf-rail-inner .uf-lane-add{order:5}' +
      '.uf-pane-row{margin-bottom:44px!important}' +
      '.uf-collapse{display:none!important}' +
      'body.uf-lane-top .uf-rail-inner{position:static!important;width:100%!important;justify-content:flex-start!important;gap:6px;border-bottom:1px solid rgba(128,128,128,.25)}' +
      'body.uf-lane-top .uf-rail{width:100%!important;height:44px!important}' +
      'body.uf-lane-top .uf-rail-parent{flex-direction:column!important}' +
      '}';
    document.head.appendChild(css);
    const wide = () => window.matchMedia('(min-width:1024px)').matches;
    const arrange = () => {
      const mail = document.querySelector<HTMLElement>('[data-tour="nav-mail"]');
      const nav = mail?.closest('nav'), inner = nav?.parentElement, rail = inner?.parentElement;
      if (!nav || !inner || !rail) return;
      rail.classList.add('uf-rail'); inner.classList.add('uf-rail-inner'); rail.parentElement?.classList.add('uf-rail-parent');
      const settings = inner.querySelector<HTMLElement>('[data-tour="nav-settings"]');
      settings?.classList.add('uf-lane-settings');
      // The first group: mail, calendar and contacts are links; its remaining button adds an application.
      nav.querySelectorAll('button').forEach(b => b.classList.add('uf-lane-add'));
      // Everything else in the lower group: notifications, keyboard shortcuts, the account button.
      let lower: HTMLElement | null = settings && settings.parentElement !== nav ? settings.parentElement : null;
      while (lower && lower.parentElement !== inner) lower = lower.parentElement;
      lower?.querySelectorAll('a,button').forEach(el => { if (el !== settings) el.classList.add('uf-lane-hide'); });
      const folders = document.querySelector<HTMLElement>('[data-tour="sidebar"]'), pane = folders?.parentElement, head = pane?.firstElementChild;
      const row = head && head !== folders ? head.firstElementChild as HTMLElement | null : null;
      document.body.classList.toggle('uf-lane-top', !row);
      if (!row || !pane) return;
      row.classList.add('uf-pane-row');
      // The fold button is the row's button without a text (the account name is the other one).
      const fold = Array.from(row.querySelectorAll<HTMLButtonElement>('button')).find(b => !(b.textContent || '').trim());
      if (fold) {
        // A pane folded earlier is opened once, then its fold button goes.
        if (wide() && pane.getBoundingClientRect().width < 160 && !fold.dataset.ufOpened) { fold.dataset.ufOpened = '1'; fold.click(); }
        fold.classList.add('uf-collapse');
      }
      document.documentElement.style.setProperty('--uf-lane-top', Math.round(row.getBoundingClientRect().bottom) + 'px');
      document.documentElement.style.setProperty('--uf-lane-width', Math.round(pane.getBoundingClientRect().width) + 'px');
    };
    let queued = false;
    const observer = new MutationObserver(() => { if (!queued) { queued = true; window.requestAnimationFrame(() => { queued = false; arrange(); }); } });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener('resize', arrange); arrange();
    return () => { observer.disconnect(); window.removeEventListener('resize', arrange); css.remove(); };
  }, []);
  return null;
}
