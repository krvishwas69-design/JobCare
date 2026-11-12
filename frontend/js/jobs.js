(function () {
  'use strict';

  var $ = function (selector) { return document.querySelector(selector); };
  var state = { jobs: [], selectedJob: null, query: '' };

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char];
    });
  }

  function formatSalary(job) {
    if (!job.min_salary && !job.max_salary) return '';
    var low = Number(job.min_salary || 0).toLocaleString('en-IN');
    var high = Number(job.max_salary || 0).toLocaleString('en-IN');
    return job.min_salary && job.max_salary ? '₹' + low + '–₹' + high + ' / month'
      : '₹' + (job.min_salary ? low : high) + ' / month';
  }

  function renderJobs() {
    var visible = state.jobs.filter(function (job) {
      return (job.title + ' ' + job.location + ' ' + job.category + ' ' + job.company)
        .toLowerCase().indexOf(state.query.toLowerCase()) !== -1;
    });
    $('#results-count').textContent = visible.length + (visible.length === 1 ? ' job' : ' jobs');
    $('#jobs-message').hidden = visible.length > 0;
    $('#jobs-message').textContent = state.jobs.length ? 'No open positions match that search.' : 'There are no open positions right now. Please check back soon.';
    $('#jobs-list').innerHTML = visible.map(function (job) {
      var facts = [job.location, job.job_type, job.category, formatSalary(job),
        job.openings + (job.openings === 1 ? ' opening' : ' openings')].filter(Boolean);
      return '<article class="job-card"><div><h3>' + esc(job.title) + '</h3>' +
        '<p class="company">' + esc(job.company || 'Employer') + '</p><div class="facts">' +
        facts.map(function (fact) { return '<span class="fact">' + esc(fact) + '</span>'; }).join('') +
        '</div>' + (job.description ? '<p class="description">' + esc(job.description) + '</p>' : '') +
        '</div><button class="apply-button" type="button" data-apply="' + job.id + '">Apply now</button></article>';
    }).join('');
  }

  async function loadJobs(query) {
    state.query = (query || '').trim();
    $('#jobs-message').hidden = false;
    $('#jobs-message').textContent = 'Loading jobs…';
    $('#jobs-list').innerHTML = '';
    try {
      state.jobs = await API.publicJobs(state.query);
      renderJobs();
    } catch (error) {
      $('#jobs-message').hidden = false;
      $('#jobs-message').textContent = error.message || 'Could not load jobs. Please try again.';
    }
  }

  function openApplication(jobId) {
    state.selectedJob = state.jobs.filter(function (job) { return job.id === Number(jobId); })[0];
    if (!state.selectedJob) return;
    $('#selected-job').textContent = state.selectedJob.title + ' · ' + (state.selectedJob.company || 'Employer') + ' · ' + state.selectedJob.location;
    $('#application-message').textContent = '';
    $('#application-form-wrap').hidden = false;
    $('#application-success').hidden = true;
    $('#apply-panel').hidden = false;
    $('#apply-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    $('#application-form').elements.name.focus();
  }

  function closeApplication() {
    $('#apply-panel').hidden = true;
    state.selectedJob = null;
  }

  async function submitApplication(event) {
    event.preventDefault();
    if (!state.selectedJob) return;

    var form = event.currentTarget;
    var values = new FormData(form);
    var payload = {
      name: String(values.get('name') || '').trim(),
      phone: String(values.get('phone') || '').trim(),
      role: String(values.get('role') || '').trim(),
      city: String(values.get('city') || '').trim(),
      area: String(values.get('area') || '').trim(),
      experience: String(values.get('experience') || '').trim(),
      skills: String(values.get('skills') || '').split(',').map(function (skill) { return skill.trim(); }).filter(Boolean).slice(0, 20),
      consent: values.get('consent') === 'on'
    };
    var button = $('#submit-application');
    button.disabled = true;
    $('#application-message').textContent = '';
    try {
      await API.applyToJob(state.selectedJob.id, payload);
      $('#application-form-wrap').hidden = true;
      $('#application-success').hidden = false;
      form.reset();
    } catch (error) {
      $('#application-message').textContent = error.message || 'Could not submit your application. Please try again.';
    } finally {
      button.disabled = false;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    $('#job-search-form').addEventListener('submit', function (event) {
      event.preventDefault();
      loadJobs($('#job-search').value);
    });
    $('#jobs-list').addEventListener('click', function (event) {
      var button = event.target.closest('[data-apply]');
      if (button) openApplication(button.dataset.apply);
    });
    $('#application-form').addEventListener('submit', submitApplication);
    $('#back-to-jobs').addEventListener('click', closeApplication);
    $('#continue-browsing').addEventListener('click', closeApplication);
    loadJobs(new URLSearchParams(location.search).get('q') || '');
  });
})();
