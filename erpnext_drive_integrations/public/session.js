/* Test-site marker (owner, 19 Nov 2026): test hostnames start with test. or test- (enforced by the renderer). */
(function(){try{if(window.top!==window||!/^test[.-]/.test(location.hostname)||document.getElementById('cloud-test-marker'))return;}catch(e){return;}var add=function(){if(document.getElementById('cloud-test-marker'))return;var s=document.createElement('style');s.textContent='#cloud-test-marker{position:fixed;top:0;left:0;right:0;height:3px;background:repeating-linear-gradient(135deg,#e8590c 0 12px,#f59f00 12px 24px);z-index:2147483647;pointer-events:none}#cloud-test-marker span{position:absolute;top:3px;left:50%;transform:translateX(-50%);background:#e8590c;color:#fff;font:600 10px/14px system-ui,sans-serif;letter-spacing:.08em;padding:0 8px;border-radius:0 0 4px 4px;opacity:.92}';var d=document.createElement('div');d.id='cloud-test-marker';d.setAttribute('aria-hidden','true');d.innerHTML='<span>TEST SITE</span>';document.head.appendChild(s);document.body.appendChild(d);};if(document.body)add();else document.addEventListener('DOMContentLoaded',add);})();
/* Shared-browser logout guard. This script grants no access and stores no token. */
(() => {
  if (window.__cloudSessionGuard || location.hostname.startsWith('respond')) return;
  window.__cloudSessionGuard = true;
  if (location.pathname === '/signed-out') return;
  // Bare Desk fallback for browsers without Fetch Metadata headers.
  if (location.hostname === 'erp.example.com' && location.pathname.replace(/\/$/, '') === '/desk' && window.self === window.top) {
    location.replace('https://erp.example.com/'); return;
  }
  // A portal app page opened on its own (new tab, pasted link, or a
  // service-worker navigation the server cannot classify) reopens inside the
  // portal, which provides the left-edge app menu. Never inside a frame or an
  // installed app window.
  const portalApp = path => path.startsWith('/desk/') && path !== '/desk/cloud-apps' || /^\/insights(\/|$)/.test(path);
  if (location.hostname === 'erp.example.com' && window.self === window.top && portalApp(location.pathname)
      && !(window.matchMedia && matchMedia('(display-mode: standalone)').matches)) {
    location.replace('/?' + new URLSearchParams({ open: location.pathname + location.search })); return;
  }
  const finish = 'https://erp.example.com/api/method/erpnext_drive_integrations.portal.sso.finish_logout';
  const portal = () => {
    if ((location.hostname === 'suite.example.com' && ['/', '/suite', '/apps'].includes(location.pathname)) || (location.hostname === 'erp.example.com' && ['/suite','/apps'].includes(location.pathname))) {
      location.replace('https://erp.example.com/desk');
    }
  };
  portal();
  if (location.hostname !== 'erp.example.com') for (const method of ['pushState', 'replaceState']) {
    const original = history[method];
    history[method] = function (...args) { const result = original.apply(this, args); portal(); return result; };
  }
  addEventListener('popstate', portal);
  // Keep the native server logout, removing only the redundant confirmation.
  const installOneShotLogout = () => {
    const app = window.frappe?.app;
    if (!app || app.logout?.cloudOneShot) return;
    const logout = function () {
      return frappe.call({method: 'logout', callback: function (r) {
        if (r.exc) return;
        app.logged_out = true;
        if (window.self !== window.top) window.parent.postMessage({source:'cloud-session',type:'logout'}, 'https://erp.example.com');
        else location.replace(finish);
      }});
    };
    logout.cloudOneShot = true; app.logout = logout;
  };
  installOneShotLogout(); setInterval(installOneShotLogout, 500);
  let busy = false, checking = false;
  // Bounded requests: a stalled connection (for example after computer sleep)
  // must not leave checks waiting forever or piling up.
  const timedFetch = (url, options = {}, ms = 8000) => {
    const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), ms);
    return fetch(url, {...options, signal: ctl.signal}).finally(() => clearTimeout(timer));
  };
  const epoch = () => document.cookie.split(';').find(v => v.trim().startsWith('cloud_logout_epoch='))?.trim() || '';
  const initialEpoch = epoch();
  const changed = () => epoch() !== initialEpoch;
  const pending = () => document.cookie.split(';').some(v => v.trim() === 'cloud_logout_pending=1');
  const check = async () => {
    if (busy || location.pathname.includes('finish_logout')) return;
    if (pending()) { busy = true; if (window.self !== window.top) { window.parent.postMessage({source:'cloud-session',type:'logout'},'https://erp.example.com'); } else location.replace(finish); return; }
    if (changed()) { busy = true; document.body?.replaceChildren(); sessionStorage.clear(); localStorage.clear(); location.replace('/signed-out'); return; }
    // A test data restore deliberately replaces ERP sessions. Keep its
    // progress-only home visible until it can renew through normal SSO.
    // Explicit logout signals above still take precedence; server permissions
    // continue to protect every authenticated request.
    if (document.getElementById('ph-test-refresh')?.dataset.refreshActive === 'true') return;
    // The server checks every authenticated request. This refreshes an open tab
    // promptly after logout in another application, and on browser back/restore.
    if (document.visibilityState !== 'visible' || location.pathname === '/login' || checking) return;
    checking = true;
    try {
      const r = await timedFetch('/api/method/erpnext_drive_integrations.portal.sso.session_status', { credentials: 'same-origin', cache: 'no-store' });
      const body = await r.json();
      if (r.status === 401 || r.status === 403 || body.message?.authenticated === false) {
        busy = true;
        location.replace('/signed-out');
      }
    } catch (_) { /* Never treat a failed check as authentication. */ }
    finally { checking = false; }
  };
  setInterval(() => { if (pending() || changed()) check(); }, 500);
  setInterval(check, 5000);
  addEventListener('pageshow', check);
  addEventListener('focus', check);
  document.addEventListener('visibilitychange', check);

  // P01 idle recovery. The SSO proxy session in front of ERP (8 hours) can
  // expire while Frappe's own session is still valid. session_status bypasses
  // the proxy, so it keeps reporting "signed in", while every background Desk
  // request is redirected to SSO and blocked by the browser: menus stop
  // responding until a reload. Detect that state through a proxy-protected
  // endpoint and renew it exactly as a reload would (normal SSO redirect, in a
  // hidden same-origin frame). If renewal needs interaction, ask the user to
  // reload instead of reloading for them, so unsaved work is not discarded.
  if (location.hostname !== 'erp.example.com') return;
  const probeUrl = '/api/method/frappe.auth.get_logged_user';
  let proxyBusy = false, lastProbe = 0, notice = null;
  const proxyExpired = async () => {
    const r = await timedFetch(probeUrl, { credentials: 'same-origin', cache: 'no-store', redirect: 'manual' });
    return r.type === 'opaqueredirect' || (r.status >= 300 && r.status < 400) || r.status === 401;
  };
  const renew = () => new Promise(resolve => {
    const frame = document.createElement('iframe');
    frame.hidden = true; frame.tabIndex = -1; frame.setAttribute('aria-hidden', 'true');
    let timer;
    const done = () => { clearTimeout(timer); frame.remove(); resolve(); };
    timer = setTimeout(done, 15000);
    frame.addEventListener('load', done, { once: true });
    frame.src = probeUrl + '?renew=' + Date.now();
    document.body.append(frame);
  });
  const hideNotice = () => { notice?.remove(); notice = null; };
  const showNotice = () => {
    if (notice) return;
    notice = document.createElement('div');
    notice.setAttribute('role', 'alert');
    notice.style.cssText = 'position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:2147483647;display:flex;gap:12px;align-items:center;max-width:calc(100vw - 32px);padding:10px 14px;border-radius:8px;background:#1f2937;color:#fff;font:14px/1.4 system-ui,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.25)';
    const text = document.createElement('span');
    text.textContent = 'Your sign-in expired while this page was idle. Copy any unsaved text, then reload to continue.';
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = 'Reload';
    button.style.cssText = 'flex:none;padding:4px 12px;border:0;border-radius:6px;background:#fff;color:#1f2937;font:inherit;font-weight:600;cursor:pointer';
    button.onclick = () => location.reload();
    notice.append(text, button);
    document.body.append(notice);
  };
  const reconnectRealtime = () => {
    try { const s = window.frappe?.realtime?.socket; if (s && !s.connected) s.connect(); } catch (_) {}
  };
  const recoverProxy = async (force) => {
    if (proxyBusy || busy || !document.body || document.visibilityState !== 'visible' || location.pathname === '/login') return;
    if (!force && Date.now() - lastProbe < 60000) return;
    proxyBusy = true; lastProbe = Date.now();
    try {
      // Valid session: still restore realtime, which gives up after three
      // failed retries (for example while the network was down during sleep).
      if (!(await proxyExpired())) { hideNotice(); reconnectRealtime(); return; }
      await renew();
      if (await proxyExpired()) showNotice(); else { hideNotice(); reconnectRealtime(); }
    } catch (_) { /* Offline or timed out: leave the page alone; retry on the next resume. */ }
    finally { proxyBusy = false; }
  };
  // Resume signals probe immediately; ordinary interaction probes at most once
  // a minute. No timer probes, so an unattended tab does not hold the SSO
  // proxy session open.
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') recoverProxy(true); });
  addEventListener('pageshow', () => recoverProxy(true));
  addEventListener('online', () => recoverProxy(true));
  addEventListener('focus', () => recoverProxy(false));
  addEventListener('pointerdown', () => recoverProxy(false), { capture: true, passive: true });
  addEventListener('keydown', () => recoverProxy(false), { capture: true, passive: true });
})();
