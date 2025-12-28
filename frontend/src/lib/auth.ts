import api from './api';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'student' | 'professor' | 'admin';
  student_id?: string;
  department?: string;
  year_level?: number;
  is_active: boolean;
  is_verified: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  role: 'student' | 'professor';
  student_id?: string;
  department?: string;
  year_level?: number;
}

export const authService = {
  async login(credentials: LoginCredentials) {
    const response = await api.post('/api/auth/login-json', credentials);
    const { access_token, user } = response.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    return { token: access_token, user };
  },

  async register(data: RegisterData) {
    const response = await api.post('/api/auth/register', data);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  getToken(): string | null {
    return localStorage.getItem('token');
  },
};

