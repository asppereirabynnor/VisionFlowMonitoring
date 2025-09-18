import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import jwt_decode from 'jwt-decode';
import { loginUser } from '../services/authService';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

interface TokenPayload {
  sub: string;
  email: string;
  role: string;
  exp: number;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    setUser(null);
    setToken(null);
    setIsAuthenticated(false);
    navigate('/login');
  }, [navigate]);

  useEffect(() => {
    // Verifica se existe um token salvo
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      try {
        // Decodifica o token para obter as informações do usuário
        const decoded = jwt_decode<TokenPayload>(storedToken);
        setToken(storedToken);
        
        // Verifica se o token está expirado
        if (decoded.exp * 1000 < Date.now()) {
          // Token expirado, faz logout
          handleLogout();
        } else {
          // Token válido, configura o usuário
          setUser({
            id: parseInt(decoded.sub),
            username: decoded.sub,
            email: decoded.email,
            role: decoded.role
          });
          setIsAuthenticated(true);
        }
      } catch (error) {
        console.error('Erro ao decodificar token:', error);
        handleLogout();
      }
    }
    setLoading(false);
  }, [handleLogout]);

  const handleLogin = async (username: string, password: string): Promise<boolean> => {
    try {
      setLoading(true);
      const response = await loginUser(username, password);
      
      if (response.access_token) {
        localStorage.setItem('token', response.access_token);
        setToken(response.access_token);
        
        // Decodifica o token para obter as informações do usuário
        const decoded = jwt_decode<TokenPayload>(response.access_token);
        
        setUser({
          id: parseInt(decoded.sub),
          username: decoded.sub,
          email: decoded.email,
          role: decoded.role
        });
        
        setIsAuthenticated(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Erro ao fazer login:', error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        token,
        login: handleLogin,
        logout: handleLogout,
        loading
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
