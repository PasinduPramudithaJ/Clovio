import { create } from 'zustand';
import { User } from '@/lib/auth';
import { authService } from '@/lib/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  loadUser: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: authService.getStoredUser(),
  isAuthenticated: !!authService.getToken(),
  isLoading: false,

  login: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      const { user } = await authService.login({ email, password });
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false });
      // Re-throw with better error message if needed
      throw error;
    }
  },

  register: async (data: any) => {
    set({ isLoading: true });
    try {
      await authService.register(data);
      // Auto-login after registration
      const { user } = await authService.login({
        email: data.email,
        password: data.password,
      });
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false });
      // Re-throw to let the component handle the error message
      throw error;
    }
  },

  logout: () => {
    authService.logout();
    set({ user: null, isAuthenticated: false });
  },

  loadUser: async () => {
    const token = authService.getToken();
    if (token) {
      try {
        const user = await authService.getCurrentUser();
        set({ user, isAuthenticated: true });
      } catch (error: any) {
        // Only logout if it's a real authentication error, not a network error
        const status = error.response?.status;
        const isAuthError = status === 401 || status === 403;
        
        if (isAuthError) {
          // Real auth error - clear tokens
          authService.logout();
          set({ user: null, isAuthenticated: false });
        } else {
          // Network or other error - keep token but mark as not loaded
          console.warn('Failed to load user, but keeping token:', error.message);
        }
      }
    }
  },
}));

