// frontend/src/lib/auth/types.ts
import { ANONYMOUS_USER_ID, ANONYMOUS_USERNAME } from '../constants';

export interface UserContext {
  id: string;
  username: string;
  email?: string;
  isAuthenticated: boolean;
}

export class UserContextHelper {
  static anonymous(): UserContext {
    return {
      id: ANONYMOUS_USER_ID,
      username: ANONYMOUS_USERNAME,
      isAuthenticated: false
    };
  }

  static authenticated(id: string, username: string, email: string): UserContext {
    return {
      id,
      username,
      email,
      isAuthenticated: true
    };
  }

  static isAuthenticated(user: UserContext): boolean {
    return user.isAuthenticated && user.id !== ANONYMOUS_USER_ID;
  }
}