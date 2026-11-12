/* Thin client for the JobCare REST API (token auth). Exposes window.API. */
(function () {
  var cfg = window.JOBCARE_CONFIG || {};
  var base = (cfg.API_BASE || '').replace(/\/+$/, '');
  var isLocal = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  if (!base && ((isLocal && location.port && location.port !== '8000') || location.protocol === 'file:')) {
    base = 'http://localhost:8000';
  }

  var KEY = 'jobcare_token';
  var store = {
    get: function () { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set: function (v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch (e) {} }
  };

  function ApiError(message, status, code) {
    this.name = 'ApiError'; this.message = message; this.status = status; this.code = code;
  }
  ApiError.prototype = Object.create(Error.prototype);

  async function request(method, path, body) {
    var headers = { Accept: 'application/json' };
    var token = store.get();
    if (token) headers.Authorization = 'Token ' + token;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    var res;
    try {
      res = await fetch(base + '/api' + path, {
        method: method, headers: headers, body: body !== undefined ? JSON.stringify(body) : undefined
      });
    } catch (e) {
      var message = isLocal && base === 'http://localhost:8000'
        ? 'Cannot connect to the Job Care API at http://localhost:8000. Start the backend with "python manage.py runserver" from the backend folder. If it is running, make sure local development has DEBUG=True so the frontend origin is allowed.'
        : 'Cannot reach the Job Care API. Check that the backend is online and API_BASE in frontend/js/config.js points to it.';
      throw new ApiError(message, 0);
    }
    if (res.status === 204) return null;
    var data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON body */ }
    if (!res.ok) {
      if (res.status === 401 && token) {
        store.set(null);
        window.dispatchEvent(new Event('jobcare:auth-expired'));
      }
      throw new ApiError((data && data.detail) || 'Request failed (' + res.status + ').', res.status, data && data.code);
    }
    return data;
  }

  function qs(params) {
    var parts = [];
    Object.keys(params || {}).forEach(function (k) {
      if (params[k]) parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(params[k]));
    });
    return parts.length ? '?' + parts.join('&') : '';
  }

  window.API = {
    ApiError: ApiError,
    hasToken: function () { return !!store.get(); },
    register: async function (payload) { var r = await request('POST', '/auth/register/', payload); store.set(r.token); return r.user; },
    login: async function (payload) { var r = await request('POST', '/auth/login/', payload); store.set(r.token); return r.user; },
    logout: async function () { try { await request('POST', '/auth/logout/'); } catch (e) {} store.set(null); },
    me: function () { return request('GET', '/auth/me/'); },
    updateMe: function (p) { return request('PATCH', '/auth/me/', p); },
    jobs: function () { return request('GET', '/jobs/'); },
    createJob: function (p) { return request('POST', '/jobs/', p); },
    updateJob: function (id, p) { return request('PATCH', '/jobs/' + id + '/', p); },
    deleteJob: function (id) { return request('DELETE', '/jobs/' + id + '/'); },
    activateJob: function (id, plan) { return request('POST', '/jobs/' + id + '/activate/', { plan: plan }); },
    closeJob: function (id) { return request('POST', '/jobs/' + id + '/close/'); },
    duplicateJob: function (id) { return request('POST', '/jobs/' + id + '/duplicate/'); },
    candidates: function (q) { return request('GET', '/candidates/' + qs({ q: q })); },
    unlockCandidate: function (id) { return request('POST', '/candidates/' + id + '/unlock/'); },
    reports: function () { return request('GET', '/reports/'); },
    invoices: function () { return request('GET', '/billing/invoices/'); },
    purchase: function (pack) { return request('POST', '/billing/purchase/', { pack: pack }); },
    applications: function () { return request('GET', '/applications/'); },
    updateApplication: function (id, payload) { return request('PATCH', '/applications/' + id + '/', payload); },
    publicJobs: function (q) { return request('GET', '/public/jobs/' + qs({ q: q })); },
    applyToJob: function (id, payload) { return request('POST', '/public/jobs/' + id + '/apply/', payload); },
    verifyPayment: function (payload) { return request('POST', '/billing/verify/', payload); }
  };
})();
