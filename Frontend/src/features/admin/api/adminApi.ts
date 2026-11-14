import { apiRequest } from "@/shared/lib/apiClient";
import { Document } from "@/features/documents/types";
import { User } from "@/shared/types";
import { workspaceApi } from "@/shared/lib/workspaceApi";

export const adminApi = {
  listUsers: workspaceApi.users,
  listTeams: workspaceApi.allTeams,
  createTeam: workspaceApi.createTeam,
  teamMembers: workspaceApi.teamMembers,
  assignUserToTeam: workspaceApi.addTeamMember,
  removeUserFromTeam: workspaceApi.removeTeamMember,
  setUserRole: workspaceApi.updateUserRole,
  setAccountingAccess: workspaceApi.setAccountingAccess,
  setUserManagementAccess: workspaceApi.setUserManagementAccess,
  setTokenLimit: workspaceApi.setTokenLimit,
  extendTokenLimit: workspaceApi.extendTokenLimit,
  resetTokenUsage: workspaceApi.resetTokenUsage,
  tokenUsage: workspaceApi.tokenUsage,
  quotaOverview: workspaceApi.quotaOverview,
  setQuotaEnforced: workspaceApi.setQuotaEnforced,
  setQuotaPlan: workspaceApi.setQuotaPlan,
  setSetupPool: workspaceApi.setSetupPool,
  setOrgCap: workspaceApi.setOrgCap,
  userQuota: workspaceApi.userQuota,
  setUserQuota: workspaceApi.setUserQuota,
  modelPrices: workspaceApi.modelPrices,
  setModelPrice: workspaceApi.setModelPrice,
  costSummary: workspaceApi.costSummary,
  updateBranding: workspaceApi.updateBranding,
  uploadBrandLogo: workspaceApi.uploadBrandLogo,
  deleteBrandLogo: workspaceApi.deleteBrandLogo,
  listAllDocuments: () => apiRequest<Document[]>("/admin/documents"),
};

export type AdminUser = User;
