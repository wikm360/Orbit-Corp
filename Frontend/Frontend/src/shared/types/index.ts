export type UserRole = "admin" | "user";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  created_at: string;
}

export interface Team {
  id: string;
  name: string;
}
