// Serviço de autenticação
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const loginUser = async (username: string, password: string): Promise<LoginResponse> => {
  try {
    // Faz a chamada real para o backend para autenticar o usuário
    const response = await axios.post(`${API_URL}/auth/token`, 
      new URLSearchParams({
        username,
        password,
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );
    
    // Armazena o token no localStorage
    localStorage.setItem('token', response.data.access_token);
    
    return response.data;
  } catch (error) {
    console.error('Erro ao fazer login:', error);
    throw new Error('Credenciais inválidas ou servidor indisponível');
  }
};

export const getCurrentUser = async () => {
  const token = localStorage.getItem('token');
  
  if (!token) {
    throw new Error('No token found');
  }
  
  try {
    // Faz a chamada real para o backend para obter informações do usuário atual
    const response = await axios.get(`${API_URL}/auth/users/me`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Erro ao obter usuário atual:', error);
    localStorage.removeItem('token'); // Remove o token inválido
    throw new Error('Sessão expirada ou inválida');
  }
};

// Função para verificar se o usuário está autenticado
export const isAuthenticated = (): boolean => {
  return localStorage.getItem('token') !== null;
};

// Função para fazer logout
export const logout = (): void => {
  localStorage.removeItem('token');
};
