/* JobCare employer portal - UI logic. Talks to the backend through window.API. */
(function () {
  'use strict';

  // ---------- helpers ----------
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  var inr = function (n) { return '₹' + Number(n || 0).toLocaleString('en-IN'); };
  function fmtDate(iso) {
    var d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  }
  var toastTimer;
  function toast(msg, isError) {
    var el = $('#toast-notice');
    el.textContent = msg;
    el.classList.toggle('error', !!isError);
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove('show'); }, isError ? 4500 : 3000);
  }
  window.toast = toast;
  function openModal(id) { var m = $('#' + id); if (m) m.classList.add('open'); }
  function closeModal(id) { var m = $('#' + id); if (m) m.classList.remove('open'); }
  function closePopovers() { $('#credits-popover').classList.remove('open'); $('#user-menu-popover').classList.remove('open'); $$('.job-menu.open').forEach(function (m) { m.classList.remove('open'); }); }
  function fail(err) { toast(err && err.message ? err.message : 'Something went wrong.', true); }
  async function busy(btn, fn) {
    if (btn) btn.disabled = true;
    try { return await fn(); } finally { if (btn) btn.disabled = false; }
  }

  // ---------- state ----------
  var state = { user: null, jobs: [], candidates: [], applications: [], filter: 'all', jobQuery: '', editingId: null, planJobId: null, plan: 'credit', authMode: 'login' };
  var FILTER_LABEL = { all: 'All Jobs', draft: 'Drafts / Incomplete', active: 'Active', closed: 'Closed' };

  // ---------- user + credits ----------
  function setUser(u) {
    state.user = u;
    var name = u.name || 'Recruiter';
    $('#top-user-avatar').textContent = u.initial;
    $('#sidebar-user-avatar').textContent = u.initial;
    $('#sidebar-user-name').textContent = name;
    $('#menu-user-name').textContent = name;
    $('#menu-user-role').textContent = u.company || 'Recruiter Admin';
    $('#pop-job-credits').textContent = u.has_unlimited ? 'Unlimited' : u.job_credits + ' credits';
    $('#pop-db-credits').textContent = u.db_credits + ' credits';
    $('#pop-slots').textContent = u.active_slots + (u.active_slots === 1 ? ' slot' : ' slots');
    $('#cred-job').textContent = u.has_unlimited ? '∞' : u.job_credits;
    $('#cred-db').textContent = u.db_credits;
    var note = $('#cred-job-note');
    if (u.has_unlimited) { note.textContent = 'Unlimited plan valid till ' + fmtDate(u.unlimited_until); note.style.color = '#10b981'; }
    else if (u.job_credits < 1) { note.textContent = '⚠️ Recharge to publish new jobs'; note.style.color = '#f59e0b'; }
    else { note.textContent = 'Each published job uses 1 credit'; note.style.color = '#6b7280'; }
  }

  // ---------- auth ----------
  function setAuthMode(mode) {
    state.authMode = mode;
    var form = $('#form-login');
    form.classList.toggle('mode-login', mode === 'login');
    $$('.auth-tab').forEach(function (t) { t.classList.toggle('active', t.dataset.authMode === mode); });
    $('#btn-submit-login').textContent = mode === 'login' ? 'Sign in' : 'Create account & continue';
    $('#auth-subtitle').textContent = mode === 'login'
      ? 'Sign in to manage your job postings, candidate database, and hiring credits.'
      : 'Create an employer account to post jobs and find candidates.';
    $('#login-password').setAttribute('autocomplete', mode === 'login' ? 'current-password' : 'new-password');
    $('#auth-error').textContent = '';
  }
  function showLogin(message) {
    closePopovers();
    setAuthMode('login');
    if (message) $('#auth-error').textContent = message;
    openModal('modal-login');
    setTimeout(function () { $('#login-phone').focus(); }, 50);
  }
  async function submitAuth(e) {
    e.preventDefault();
    var err = $('#auth-error'); err.textContent = '';
    var identifier = $('#login-phone').value.trim(), password = $('#login-password').value;
    var register = state.authMode === 'register';
    var name = $('#login-name').value.trim();
    if (register && !name) { err.textContent = 'Please enter your full name.'; return; }
    if (!identifier || !password) { err.textContent = 'Enter your mobile/email and password.'; return; }
    await busy($('#btn-submit-login'), async function () {
      try {
        var user = register
          ? await API.register({ name: name, company: $('#login-company').value.trim(), identifier: identifier, password: password })
          : await API.login({ identifier: identifier, password: password });
        $('#login-password').value = '';
        closeModal('modal-login');
        setUser(user);
        toast(register ? 'Welcome to JobCare, ' + user.name + '!' : 'Welcome back, ' + user.name + '!');
        await loadAll();
      } catch (ex) { err.textContent = ex.message; }
    });
  }
  async function logout() {
    closePopovers();
    await API.logout();
    state.user = null; state.jobs = []; state.candidates = [];
    renderJobs(); renderCandidates();
    showLogin();
  }

  // ---------- data loading ----------
  async function loadJobs() { try { state.jobs = await API.jobs(); renderJobs(); } catch (e) { fail(e); } }
  async function loadCandidates() {
    try { state.candidates = await API.candidates($('#candidate-search-input').value.trim()); renderCandidates(); } catch (e) { fail(e); }
  }
  async function loadReports() {
    try {
      var r = await API.reports(), pct = function (n, d) { return d ? Math.round(n * 100 / d) : 0; };
      $('#rep-active').textContent = r.jobs.active;
      $('#rep-apps').textContent = r.applications;
      $('#rep-contacted').textContent = r.contacted;
      $('#rep-hired').textContent = r.hired;
      $('#fun-applied-txt').textContent = r.applications + ' (100%)';
      $('#fun-short-txt').textContent = r.shortlisted + ' (' + pct(r.shortlisted, r.applications) + '%)';
      $('#fun-hired-txt').textContent = r.hired + ' (' + pct(r.hired, r.applications) + '%)';
      $('#fun-applied').style.width = (r.applications ? 100 : 0) + '%';
      $('#fun-short').style.width = pct(r.shortlisted, r.applications) + '%';
      $('#fun-hired').style.width = pct(r.hired, r.applications) + '%';
      $('#rep-jobs-note').textContent = r.jobs.total + ' jobs posted: ' + r.jobs.active + ' active, ' + r.jobs.draft + ' draft, ' + r.jobs.closed + ' closed.';
    } catch (e) { fail(e); }
  }
  async function loadInvoices() {
    try {
      var list = await API.invoices(), body = $('#invoices-body');
      $('#invoices-empty').hidden = list.length > 0;
      body.innerHTML = list.map(function (i) {
        return '<tr><td><b>' + esc(i.number) + '</b></td><td>' + fmtDate(i.created_at) + '</td><td>' + esc(i.plan) + '</td><td><b>' + inr(i.amount) +
          '</b></td><td><span class="paid">' + esc(i.status) + '</span></td><td><button class="link-btn" data-invoice="' + i.id + '">Download PDF</button></td></tr>';
      }).join('');
      body._invoices = list;
    } catch (e) { fail(e); }
  }
  async function loadApplications() {
    try {
      state.applications = await API.applications();
      var body = $('#applications-body');
      $('#applications-empty').hidden = state.applications.length > 0;
      body.innerHTML = state.applications.map(function (a) {
        var phone = String(a.candidate_phone || '').replace(/[^\d+]/g, '');
        var statuses = ['applied', 'shortlisted', 'interviewed', 'hired', 'rejected'];
        return '<tr><td><b>' + esc(a.candidate_name) + '</b>' +
          (a.candidate_role ? '<br><span style="color:#6b7280">' + esc(a.candidate_role) + '</span>' : '') +
          '</td><td>' + esc(a.job_title) + '</td><td>' + (phone ? '<a href="tel:' + esc(phone) + '">' + esc(a.candidate_phone) + '</a>' : '—') +
          '</td><td>' + fmtDate(a.applied_at) + '</td><td><select class="form-input" data-application-status="' + a.id + '" aria-label="Application status for ' + esc(a.candidate_name) + '">' +
          statuses.map(function (status) { return '<option value="' + status + '"' + (a.status === status ? ' selected' : '') + '>' + status.charAt(0).toUpperCase() + status.slice(1) + '</option>'; }).join('') +
          '</select></td></tr>';
      }).join('');
    } catch (e) { fail(e); }
  }
  var razorpayScriptPromise;
  function loadRazorpayCheckout() {
    if (window.Razorpay) return Promise.resolve();
    if (!razorpayScriptPromise) {
      razorpayScriptPromise = new Promise(function (resolve, reject) {
        var script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = resolve;
        script.onerror = function () {
          razorpayScriptPromise = null;
          reject(new Error('Could not load the secure payment checkout. Please try again.'));
        };
        document.head.appendChild(script);
      });
    }
    return razorpayScriptPromise;
  }
  async function loadAll() { await Promise.all([loadJobs(), loadCandidates()]); }

  // ---------- navigation ----------
  function showView(name) {
    $$('.nav-item[data-nav]').forEach(function (b) { b.classList.toggle('active', b.dataset.nav === name); });
    $$('.view-panel').forEach(function (p) { p.classList.toggle('active', p.id === 'view-' + name); });
    if (name === 'reports') loadReports();
    if (name === 'billing') loadInvoices();
    if (name === 'database') loadCandidates();
    if (name === 'applicants') loadApplications();
    if (window.innerWidth <= 800) $('#sidebar').classList.add('collapsed');
  }

  // ---------- jobs ----------
  function visibleJobs() {
    var q = state.jobQuery.toLowerCase();
    return state.jobs.filter(function (j) {
      if (state.filter !== 'all' && j.status !== state.filter) return false;
      return !q || (j.title + ' ' + j.location + ' ' + j.category).toLowerCase().indexOf(q) !== -1;
    });
  }
  function salary(j) {
    if (!j.min_salary && !j.max_salary) return '';
    return inr(j.min_salary) + ' – ' + inr(j.max_salary) + ' / month';
  }
  function renderJobs() {
    var list = visibleJobs();
    $('#jobs-count-heading').textContent = FILTER_LABEL[state.filter] + ' (' + list.length + ')';
    var box = $('#jobs-container');
    if (!list.length) {
      box.innerHTML = '<div class="empty-state">' + (state.jobs.length ? 'No jobs match this filter.' : 'You have not posted any jobs yet. Click <b>Post a new job</b> to get started.') + '</div>';
      return;
    }
    box.innerHTML = list.map(function (j) {
      var badge = j.status === 'draft' ? 'Select Plan' : j.status === 'active' ? 'Active' : 'Closed';
      var notice = j.status === 'draft'
        ? '<div class="job-notice"><span>ⓘ Finish job posting to start receiving candidates</span><button class="btn-outline" data-job-act="finish" data-id="' + j.id + '">Finish posting</button></div>'
        : j.status === 'closed'
          ? '<div class="job-notice"><span>This job is closed and not visible to candidates.</span><button class="btn-outline" data-job-act="finish" data-id="' + j.id + '">Reopen</button></div>' : '';
      var facts = [j.job_type, j.category, j.openings + (j.openings === 1 ? ' opening' : ' openings'), salary(j), j.applicants + (j.applicants === 1 ? ' applicant' : ' applicants')]
        .filter(Boolean).map(function (f) { return '<span class="job-fact">' + esc(f) + '</span>'; }).join('');
      var closeBtn = j.status === 'active' ? '<button data-job-act="close" data-id="' + j.id + '">Close</button>' : '';
      return '<article class="job-card" data-job="' + j.id + '"><div class="job-card-top"><div>' +
        '<div class="job-title-row"><h2 class="job-title">' + esc(j.title) + '</h2><span class="job-badge ' + j.status + '">' + badge + '</span></div>' +
        '<div class="job-meta"><span>' + esc(j.location) + '</span><span>Posted on : ' + fmtDate(j.created_at) + '</span><span title="Job posted by :' + esc(j.posted_by_name) + '">' + esc(j.posted_by_name) + '</span></div>' +
        '</div><div class="job-menu-wrap"><button class="job-menu-btn" data-job-act="menu" aria-label="Job actions">⋮</button>' +
        '<div class="job-menu"><button data-job-act="edit" data-id="' + j.id + '">Edit</button><button data-job-act="duplicate" data-id="' + j.id + '">Duplicate</button>' + closeBtn +
        '<button class="danger" data-job-act="delete" data-id="' + j.id + '">Delete</button></div></div></div>' +
        '<div class="job-facts">' + facts + '</div>' + notice + '</article>';
    }).join('');
  }
  function findJob(id) { return state.jobs.filter(function (j) { return j.id === Number(id); })[0]; }
  function upsertJob(job) {
    var i = state.jobs.findIndex(function (j) { return j.id === job.id; });
    if (i === -1) state.jobs.unshift(job); else state.jobs[i] = job;
    renderJobs();
  }

  function openPostModal(job) {
    state.editingId = job ? job.id : null;
    $('#modal-post-job .modal-title').textContent = job ? 'Edit Job Opening' : 'Post a New Job Opening';
    $('#btn-submit-post-job').textContent = job ? 'Save Changes' : 'Create Job';
    var v = job || { title: '', category: 'Telecaller', job_type: 'Full Time', location: 'Bengaluru/Bangalore', openings: 5, min_salary: 18000, max_salary: 28000, description: '' };
    $('#inp-job-title').value = v.title; $('#inp-job-category').value = v.category; $('#inp-job-type').value = v.job_type;
    $('#inp-job-location').value = v.location; $('#inp-job-openings').value = v.openings;
    $('#inp-min-salary').value = v.min_salary; $('#inp-max-salary').value = v.max_salary; $('#inp-job-desc').value = v.description;
    openModal('modal-post-job');
    setTimeout(function () { $('#inp-job-title').focus(); }, 50);
  }
  async function submitJob() {
    var payload = {
      title: $('#inp-job-title').value.trim(), category: $('#inp-job-category').value, job_type: $('#inp-job-type').value,
      location: $('#inp-job-location').value.trim(), openings: parseInt($('#inp-job-openings').value, 10) || 1,
      min_salary: parseInt($('#inp-min-salary').value, 10) || 0, max_salary: parseInt($('#inp-max-salary').value, 10) || 0,
      description: $('#inp-job-desc').value.trim()
    };
    if (!payload.title) return toast('Please enter a job title.', true);
    if (!payload.location) return toast('Please enter the job location.', true);
    await busy($('#btn-submit-post-job'), async function () {
      try {
        var editing = state.editingId;
        var job = editing ? await API.updateJob(editing, payload) : await API.createJob(payload);
        upsertJob(job); closeModal('modal-post-job');
        toast(editing ? 'Job updated.' : 'Job saved as draft. Click "Finish posting" to publish it.');
      } catch (e) { fail(e); }
    });
  }

  function openPlanModal(job) {
    state.planJobId = job.id;
    $('#plan-modal-job-title').textContent = job.title;
    pickPlan(state.user && state.user.has_unlimited ? 'unlimited' : 'credit');
    openModal('modal-select-plan');
  }
  function pickPlan(plan) {
    state.plan = plan;
    $$('#modal-select-plan .plan-choice-card').forEach(function (c) { c.classList.toggle('selected', c.dataset.plan === plan); });
  }
  async function confirmPlan() {
    if (state.plan === 'unlimited' && !(state.user && state.user.has_unlimited)) {
      closeModal('modal-select-plan');
      openModal('modal-view-plans');
      toast('Purchase the unlimited plan first, then activate this job.');
      return;
    }
    await busy($('#btn-confirm-plan'), async function () {
      try {
        var res = await API.activateJob(state.planJobId, state.plan);
        upsertJob(res.job); setUser(res.user); closeModal('modal-select-plan');
        toast('"' + res.job.title + '" is now live and receiving candidates!');
      } catch (e) {
        fail(e);
        if (e.code === 'no_credits' || e.status === 402) { closeModal('modal-select-plan'); openModal('modal-view-plans'); }
      }
    });
  }

  async function jobAction(act, id) {
    var job = findJob(id);
    if (act === 'finish' && job) return openPlanModal(job);
    if (act === 'edit' && job) return openPostModal(job);
    try {
      if (act === 'duplicate') { upsertJob(await API.duplicateJob(id)); toast('Job duplicated as a draft.'); }
      else if (act === 'close') { if (confirm('Close this job? Candidates will no longer see it.')) { upsertJob(await API.closeJob(id)); toast('Job closed.'); } }
      else if (act === 'delete') {
        if (confirm('Delete "' + (job ? job.title : 'this job') + '" permanently?')) {
          await API.deleteJob(id); state.jobs = state.jobs.filter(function (j) { return j.id !== Number(id); }); renderJobs(); toast('Job deleted.');
        }
      }
    } catch (e) { fail(e); }
  }

  // ---------- candidates ----------
  function renderCandidates() {
    var box = $('#candidates-container');
    if (!state.candidates.length) { box.innerHTML = '<div class="empty-state" style="grid-column:1/-1">No candidates match your search.</div>'; return; }
    box.innerHTML = state.candidates.map(function (c) {
      var chips = (c.skills || []).map(function (s) { return '<span class="skill-chip">' + esc(s) + '</span>'; }).join('');
      var action = c.unlocked
        ? '<a class="btn-outline" href="tel:' + esc(c.phone) + '">Call now</a>'
        : '<button class="btn-primary" data-unlock="' + c.id + '">Unlock phone · 1 credit</button>';
      return '<article class="candidate-card"><div class="candidate-head"><div class="candidate-avatar">' + esc((c.name || '?').charAt(0).toUpperCase()) + '</div>' +
        '<div><div class="candidate-name">' + esc(c.name) + '</div><div class="candidate-role">' + esc(c.role) + '</div></div></div>' +
        '<div class="candidate-details"><div>📍 ' + esc([c.area, c.city].filter(Boolean).join(', ')) + '</div><div>💼 ' + esc(c.experience) + ' · ' + esc(c.expected_salary) + '</div></div>' +
        '<div class="skill-chips">' + chips + '</div>' +
        '<div class="candidate-actions"><span class="candidate-phone">📞 ' + esc(c.phone) + '</span>' + action + '</div></article>';
    }).join('');
  }
  async function unlock(id, btn) {
    await busy(btn, async function () {
      try {
        var res = await API.unlockCandidate(id);
        state.candidates = state.candidates.map(function (c) { return c.id === res.candidate.id ? res.candidate : c; });
        setUser(res.user); renderCandidates(); toast('Phone number unlocked.');
      } catch (e) { fail(e); if (e.status === 402) openModal('modal-view-plans'); }
    });
  }

  // ---------- billing ----------
  async function buy(pack, btn) {
    await busy(btn, async function () {
      try {
        var res = await API.purchase(pack);
        if (res.demo) {
          setUser(res.user); closeModal('modal-view-plans'); toast(res.message);
          if ($('#view-billing').classList.contains('active')) loadInvoices();
          return;
        }
        await loadRazorpayCheckout();
        var checkout = new window.Razorpay({
          key: res.key_id,
          amount: res.amount,
          currency: res.currency,
          name: res.name,
          description: res.description,
          order_id: res.order_id,
          prefill: res.prefill,
          handler: async function (payment) {
            try {
              var verified = await API.verifyPayment(payment);
              setUser(verified.user);
              closeModal('modal-view-plans');
              toast(verified.message);
              if ($('#view-billing').classList.contains('active')) loadInvoices();
            } catch (e) {
              fail(e);
              toast('If your payment was deducted, wait for confirmation before trying again.', true);
            }
          },
          modal: { ondismiss: function () { toast('Payment was not completed. No credits were added.'); } }
        });
        checkout.on('payment.failed', function () {
          toast('Payment failed. No credits were added. Please try again.', true);
        });
        checkout.open();
      } catch (e) { fail(e); }
    });
  }
  function printInvoice(inv) {
    var w = window.open('', '_blank');
    if (!w) return toast('Allow pop-ups to download the invoice.', true);
    var u = state.user || {};
    w.document.write('<!doctype html><title>' + esc(inv.number) + '</title><body style="font-family:Arial,sans-serif;max-width:640px;margin:40px auto;color:#111">' +
      '<h1 style="margin:0">Job<span style="color:#00a877">Care</span></h1><p style="color:#666">' +
      (inv.is_demo ? 'Demo payment receipt' : 'Payment receipt') + '</p><hr>' +
      '<p><b>Invoice:</b> ' + esc(inv.number) + '<br><b>Date:</b> ' + fmtDate(inv.created_at) + '<br><b>Billed to:</b> ' + esc(u.name) + (u.company ? ', ' + esc(u.company) : '') + '</p>' +
      '<table style="width:100%;border-collapse:collapse"><tr style="background:#f3f4f6"><th align="left" style="padding:8px">Plan</th><th align="right" style="padding:8px">Amount</th></tr>' +
      '<tr><td style="padding:8px;border-bottom:1px solid #ddd">' + esc(inv.plan) + '</td><td align="right" style="padding:8px;border-bottom:1px solid #ddd">' + inr(inv.amount) + '</td></tr></table>' +
      '<p style="text-align:right"><b>Total: ' + inr(inv.amount) + '</b> (' + esc(inv.status) + ')</p><script>window.onload=function(){window.print()}<\/script></body>');
    w.document.close();
  }

  // ---------- support chat (canned answers, no live agent) ----------
  function chatReply(text) {
    var t = text.toLowerCase();
    if (/credit/.test(t)) return 'Each job you publish uses 1 job credit. Candidate phone numbers use database credits. Open "Credits & Usage" or "View plans" to top up.';
    if (/post|job|publish/.test(t)) return 'Click "Post a new job", fill in the details, then use "Finish posting" on the draft to choose a plan and publish it.';
    if (/candidate|resume|database|phone/.test(t)) return 'Use the Database tab to search by skill or city. Unlocking a candidate reveals their phone number for 1 database credit.';
    if (/bill|invoice|plan|price|pay/.test(t)) return 'Invoices for every purchase appear under Billing. Annual plans are listed under "View plans".';
    return 'Thanks for your message! A live agent is not connected yet. Try asking about credits, posting jobs, candidates or billing.';
  }
  function sendChat() {
    var input = $('#chat-input'), text = input.value.trim();
    if (!text) return;
    var box = $('#chat-messages');
    function bubble(t, cls) { var d = document.createElement('div'); d.className = 'chat-bubble' + (cls ? ' ' + cls : ''); d.textContent = t; box.appendChild(d); box.scrollTop = box.scrollHeight; }
    bubble(text, 'user'); input.value = '';
    setTimeout(function () { bubble(chatReply(text)); }, 400);
  }

  // ---------- profile ----------
  async function saveProfile() {
    await busy($('#btn-save-profile'), async function () {
      try {
        var u = await API.updateMe({ name: $('#prof-name').value.trim(), company: $('#prof-company').value.trim(), phone: $('#prof-phone').value.trim() });
        setUser(u); closeModal('modal-profile'); toast('Profile updated.');
      } catch (e) { fail(e); }
    });
  }
  function openProfile() {
    closePopovers();
    $('#prof-name').value = state.user.name; $('#prof-company').value = state.user.company; $('#prof-phone').value = state.user.phone;
    openModal('modal-profile');
  }

  // ---------- events ----------
  function bind() {
    var salesContact = window.JOBCARE_CONFIG || {};
    var salesEmail = $('#sales-email-link');
    var salesPhone = $('#sales-phone-link');
    if (salesContact.SALES_EMAIL) {
      salesEmail.href = 'mailto:' + salesContact.SALES_EMAIL + '?subject=' + encodeURIComponent('Job Care sales enquiry');
      salesEmail.textContent = 'Email ' + salesContact.SALES_EMAIL;
    } else {
      salesEmail.hidden = true;
    }
    if (salesContact.SALES_PHONE) {
      var phoneDigits = String(salesContact.SALES_PHONE).replace(/[^\d+]/g, '');
      salesPhone.href = 'tel:' + phoneDigits;
      salesPhone.textContent = 'Call ' + salesContact.SALES_PHONE;
    } else {
      salesPhone.hidden = true;
    }

    $('#form-login').addEventListener('submit', submitAuth);
    $$('.auth-tab').forEach(function (t) { t.addEventListener('click', function () { setAuthMode(t.dataset.authMode); }); });
    $('#hamburger-btn').addEventListener('click', function () { $('#sidebar').classList.toggle('collapsed'); });
    $$('.nav-item[data-nav]').forEach(function (b) { b.addEventListener('click', function () { showView(b.dataset.nav); }); });

    $('#btn-available-credits').addEventListener('click', function (e) { e.stopPropagation(); var p = $('#credits-popover'), o = p.classList.contains('open'); closePopovers(); if (!o) p.classList.add('open'); });
    $('#btn-user-avatar').addEventListener('click', function (e) { e.stopPropagation(); var p = $('#user-menu-popover'), o = p.classList.contains('open'); closePopovers(); if (!o) p.classList.add('open'); });
    ['credits-popover', 'user-menu-popover'].forEach(function (id) { $('#' + id).addEventListener('click', function (e) { e.stopPropagation(); }); });
    document.addEventListener('click', closePopovers);

    $('#menu-logout').addEventListener('click', logout);
    $('#menu-edit-profile').addEventListener('click', openProfile);
    $('#menu-account-settings').addEventListener('click', openProfile);
    $('#sidebar-user-box').addEventListener('click', openProfile);
    $('#btn-save-profile').addEventListener('click', saveProfile);
    $('#btn-dismiss-banner').addEventListener('click', function () { $('#festive-banner-box').hidden = true; try { localStorage.setItem('jobcare_banner_off', '1'); } catch (e) {} });
    try { if (localStorage.getItem('jobcare_banner_off')) $('#festive-banner-box').hidden = true; } catch (e) {}

    $('#btn-post-job').addEventListener('click', function () { openPostModal(null); });
    $('#btn-submit-post-job').addEventListener('click', submitJob);
    $('#btn-confirm-plan').addEventListener('click', confirmPlan);
    $$('#modal-select-plan .plan-choice-card').forEach(function (c) { c.addEventListener('click', function () { pickPlan(c.dataset.plan); }); });

    $$('.filter-tab-btn').forEach(function (b) {
      b.addEventListener('click', function () {
        state.filter = b.dataset.filter;
        $$('.filter-tab-btn').forEach(function (x) { x.classList.toggle('active', x === b); });
        renderJobs();
      });
    });
    $('#jobs-search-input').addEventListener('input', function (e) { state.jobQuery = e.target.value.trim(); renderJobs(); });

    $('#jobs-container').addEventListener('click', function (e) {
      var el = e.target.closest('[data-job-act]'); if (!el) return;
      e.stopPropagation();
      if (el.dataset.jobAct === 'menu') {
        var menu = el.parentNode.querySelector('.job-menu'), was = menu.classList.contains('open');
        closePopovers(); if (!was) menu.classList.add('open'); return;
      }
      closePopovers(); jobAction(el.dataset.jobAct, el.dataset.id);
    });

    var t;
    $('#candidate-search-input').addEventListener('input', function () { clearTimeout(t); t = setTimeout(loadCandidates, 300); });
    $('#candidates-container').addEventListener('click', function (e) {
      var b = e.target.closest('[data-unlock]'); if (b) unlock(b.dataset.unlock, b);
    });

    $('#invoices-body').addEventListener('click', function (e) {
      var b = e.target.closest('[data-invoice]'); if (!b) return;
      var inv = ($('#invoices-body')._invoices || []).filter(function (i) { return String(i.id) === b.dataset.invoice; })[0];
      if (inv) printInvoice(inv);
    });
    $('#btn-refresh-applicants').addEventListener('click', loadApplications);
    $('#applications-body').addEventListener('change', async function (e) {
      var select = e.target.closest('[data-application-status]');
      if (!select) return;
      select.disabled = true;
      try {
        var updated = await API.updateApplication(select.dataset.applicationStatus, { status: select.value });
        state.applications = state.applications.map(function (a) { return a.id === updated.id ? updated : a; });
        toast('Application status updated.');
      } catch (err) {
        fail(err);
        await loadApplications();
      } finally { select.disabled = false; }
    });

    document.addEventListener('click', function (e) {
      var close = e.target.closest('[data-close-modal]'); if (close) return closeModal(close.dataset.closeModal);
      var buyBtn = e.target.closest('[data-buy]'); if (buyBtn) return buy(buyBtn.dataset.buy, buyBtn);
      var act = e.target.closest('[data-act]'); if (!act) return;
      var a = act.dataset.act;
      if (a === 'view-plans' || a === 'buy-credits' || a === 'buy-unlimited') { closePopovers(); openModal('modal-view-plans'); }
      else if (a === 'help') { $('#chat-popup').classList.add('open'); }
      else if (a === 'sales') {
        if (salesContact.SALES_EMAIL || salesContact.SALES_PHONE) openModal('modal-contact-sales');
        else toast('Sales contact is not configured yet.');
      }
    });
    $$('.modal-backdrop').forEach(function (m) { m.addEventListener('mousedown', function (e) { if (e.target === m && m.id !== 'modal-login') m.classList.remove('open'); }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closePopovers(); $$('.modal-backdrop.open').forEach(function (m) { if (m.id !== 'modal-login') m.classList.remove('open'); }); } });

    $('#btn-floating-chat').addEventListener('click', function () { $('#chat-popup').classList.toggle('open'); });
    $('#btn-close-chat').addEventListener('click', function () { $('#chat-popup').classList.remove('open'); });
    $('#btn-send-chat').addEventListener('click', sendChat);
    $('#chat-input').addEventListener('keydown', function (e) { if (e.key === 'Enter') sendChat(); });

    window.addEventListener('jobcare:auth-expired', function () { showLogin('Your session expired. Please sign in again.'); });
  }

  // ---------- boot ----------
  async function boot() {
    bind();
    if (window.innerWidth <= 800) $('#sidebar').classList.add('collapsed');
    renderJobs(); renderCandidates();
    if (!API.hasToken()) return showLogin();
    try { setUser(await API.me()); await loadAll(); }
    catch (e) { if (e.status !== 401) { fail(e); } showLogin(); }
  }
  document.addEventListener('DOMContentLoaded', boot);
})();
