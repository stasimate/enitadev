// The dev server sends /api to the backend. In Docker, API_TARGET is http://backend-dev:8000.
export default {
  '/api': { target: process.env.API_TARGET ?? 'http://localhost:8000', secure: false },
};
