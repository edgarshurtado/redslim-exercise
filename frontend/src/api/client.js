import axios from 'axios'

export default axios.create({
  baseURL: import.meta.env.API_BASE_URL ?? 'http://localhost:8000'
})
