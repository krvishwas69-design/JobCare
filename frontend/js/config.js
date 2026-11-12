/* Runtime configuration. Edit this file only if the API lives on a different domain.
 *
 * Default (API_BASE = "") : the page and the API come from the same server, which is how the
 *                           Render deployment works (Django serves this folder too).
 * Split hosting           : if you host this folder on Netlify/Vercel, set API_BASE to your
 *                           backend URL, e.g. "https://jobcare-api.onrender.com", and add the
 *                           frontend URL to CORS_ALLOWED_ORIGINS on the backend.
 * Local development       : opening the page on localhost:3000 etc. automatically talks to
 *                           http://localhost:8000.
 */
window.JOBCARE_CONFIG = {
  API_BASE: "",
  SALES_EMAIL: "vkr99013@gmail.com",
  SALES_PHONE: "8762954286"
};
