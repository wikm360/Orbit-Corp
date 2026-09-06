import { User } from "@/shared/types";
import { Document } from "@/features/documents/types";

export type { Document };

export interface Team {
  id: string;
  name: string;
}

export interface UserWithTeams extends User {
  teams: Team[];
}
