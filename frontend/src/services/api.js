import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000', //mudar para quando o back estiver proto
  timeout: 5000,
});

export default api;