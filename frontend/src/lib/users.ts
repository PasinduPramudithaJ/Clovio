import api from './api';
import { User } from './auth';

export const userService = {
  /**
   * Get all users (admin only)
   */
  async getAllUsers(role?: string): Promise<User[]> {
    const params = role ? { role } : {};
    const response = await api.get('/api/users/', { params });
    return response.data;
  },

  /**
   * Get a specific user by ID
   */
  async getUserById(userId: number): Promise<User> {
    const response = await api.get(`/api/users/${userId}`);
    return response.data;
  },

  /**
   * Delete a user (admin only, cannot delete admin users)
   */
  async deleteUser(userId: number): Promise<void> {
    await api.delete(`/api/users/${userId}`);
  },
};

