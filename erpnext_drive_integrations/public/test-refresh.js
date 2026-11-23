/* P71 test-only deployment and reset drill marker. */
/* Test-only status panel. Production never renders or loads this module.
   Two actions (owner decision, 19 November 2026):
   - "Refresh code" resets the test site to the tested release (main).
   - "Refresh data" replaces test data with a scrambled copy of the last 60
     days of production (personal details replaced, documents as placeholders).
     It uses production resources, so it is meant for occasional use. */
(() => {
  'use strict';
  const panel = document.getElementById('ph-test-refresh');
  if (!panel) return;
  const buttons = [...panel.querySelectorAll('button[data-kind]')];
  const progress = panel.querySelector('[data-progress]');
  const last = panel.querySelector('[data-last-refresh]');
  const lastCode = panel.querySelector('[data-last-code]');
  const base = '/api/method/erpnext_drive_integrations.portal.test_refresh.';
  const csrf = document.querySelector('meta[name="test-refresh-csrf"]')?.content;
  let polling;
  let observedRefresh = false;
  const running = new Set(['queued', 'snapshotting', 'transferring', 'restoring', 'validating', 'updating-code']);
  const texts = {
    code: {title: 'Reset test code?',
      body: 'Put the test site back to the approved release (main)? Any branch deployed for testing is replaced. '
        + 'Test data stays as it is. Nothing changes on production.',
      confirm: 'Refresh code'},
    data: {title: 'Replace test data?',
      body: 'Replace test data in ERP, Drive, DMS and Mail with a scrambled copy of the last 60 days of production. '
        + 'Names, contact details, bank and tax numbers are replaced, documents become placeholders and test mailboxes '
        + 'start empty. This uses production resources and pauses production apps briefly; use it only when necessary. '
        + 'Nothing is copied back to production.',
      confirm: 'Refresh data'},
  };
  const format = value => value
    ? new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value))
    : 'never';
  function confirmRefresh(kind) {
    panel.querySelector('dialog')?.remove();
    const dialog = document.createElement('dialog');
    dialog.className = 'ph-refresh-confirm';
    dialog.setAttribute('aria-labelledby', 'ph-refresh-confirm-title');
    const form = document.createElement('form');
    form.method = 'dialog';
    const title = document.createElement('h3');
    title.id = 'ph-refresh-confirm-title';
    title.textContent = texts[kind].title;
    const body = document.createElement('p');
    body.textContent = texts[kind].body;
    const actions = document.createElement('div');
    const cancel = document.createElement('button');
    cancel.value = 'cancel';
    cancel.autofocus = true;
    cancel.textContent = 'Cancel';
    const ok = document.createElement('button');
    ok.value = 'confirm';
    ok.textContent = texts[kind].confirm;
    actions.append(cancel, ok);
    form.append(title, body, actions);
    dialog.append(form);
    panel.append(dialog);
    dialog.returnValue = 'cancel';
    return new Promise(resolve => {
      dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm'), {once: true});
      dialog.showModal();
    });
  }
  async function update() {
    try {
      const response = await fetch(base + 'status', {credentials: 'same-origin', cache: 'no-store'});
      if (!response.ok) throw new Error('Temporarily unavailable');
      const {message: state} = await response.json();
      last.textContent = format(state.last_successful_at);
      if (lastCode) lastCode.textContent = format(state.last_code_refresh_at) + (state.revision ? ` (${state.revision})` : '');
      const failed = state.kind === 'code'
        ? 'Code refresh failed. The test site keeps its previous code.'
        : 'Data refresh failed. The last successful refresh time is unchanged.';
      progress.textContent = ({idle: 'Test is independent of production.',
        queued: 'Request queued…', snapshotting: 'Preparing a scrambled production copy…',
        transferring: 'Copying to test…', restoring: 'Replacing test data…',
        validating: 'Checking restored data…', 'updating-code': 'Updating test code to the approved release…',
        succeeded: state.kind === 'code' ? 'Code refresh completed.' : 'Data refresh completed.',
        failed})[state.phase] || 'Checking status…';
      // Only a running, queued or failed refresh needs a line under the buttons.
      progress.hidden = state.phase === 'idle' || state.phase === 'succeeded';
      for (const button of buttons) button.disabled = running.has(state.phase);
      clearTimeout(polling);
      if (running.has(state.phase)) {
        observedRefresh = true;
        panel.dataset.refreshActive = 'true';
        polling = setTimeout(update, 5000);
      } else if (observedRefresh) {
        // Restoration quarantines native sessions; a normal home navigation
        // obtains a new session through SSO and drops stale app frames.
        polling = setTimeout(() => location.replace('/'), 1500);
      } else {
        delete panel.dataset.refreshActive;
      }
    } catch (_) {
      progress.textContent = 'Test is temporarily unavailable. Reconnecting…';
      clearTimeout(polling);
      polling = setTimeout(update, 5000);
    }
  }
  for (const button of buttons) {
    button.addEventListener('click', async () => {
      const kind = button.dataset.kind;
      if (!texts[kind] || !await confirmRefresh(kind)) return;
      panel.dataset.refreshActive = 'true';
      observedRefresh = true;
      for (const other of buttons) other.disabled = true;
      try {
        const response = await fetch(base + 'request_refresh', {method: 'POST', credentials: 'same-origin',
          headers: {'X-Frappe-CSRF-Token': csrf, 'Content-Type': 'application/json'}, body: JSON.stringify({kind})});
        if (!response.ok) throw new Error('Refresh request rejected');
        progress.textContent = 'Request queued…';
        polling = setTimeout(update, 2000);
      } catch (_) {
        delete panel.dataset.refreshActive;
        observedRefresh = false;
        progress.textContent = 'Could not send the request. Sign in again or ask a test administrator.';
        for (const other of buttons) other.disabled = false;
      }
    });
  }
  update();
})();
