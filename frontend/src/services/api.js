import axios from 'axios';

const api = axios.create({
  baseURL: '/api', // Esto se proxy a http://localhost:8000/api
  withCredentials: true, // Para incluir cookies de sesión
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para manejar errores globalmente
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirigir a login si no está autenticado
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Función para cargar archivo Excel
export const cargarExcel = async (file) => {
  const formData = new FormData();
  formData.append('archivo', file);

  try {
    const response = await axios.post('/api/cargar-excel/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    if (error.response?.data) {
      throw error.response.data;
    }
    throw new Error('Error al cargar el archivo');
  }
};

export default api;