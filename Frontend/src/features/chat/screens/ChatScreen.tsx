"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, workspaceApi } from "@/shared/lib/workspaceApi";
import { Project } from "@/shared/types";
import { Document } from "@/features/documents/types";
import { documentsApi } from "@/features/documents/api/documentsApi";
import { chatApi } from "../api/chatApi";
import { ChatWindow } from "../components/ChatWindow";
import { useChat } from "../hooks/useChat";

export function ChatScreen() {
  const { conversation, conversationId, messages, isStreaming, agentStatusText, isLoadingConversation, error, sendMessage, loadConversation, startNewConversation, linkProject } = useChat();
  const user = useAuthStore((state) => state.user);
  const router = useRouter();
  const searchParams = useSearchParams();
  const lastRouteAction = useRef<string | null>(null);
  const selectedConversationId = searchParams.get("conversation");
  const newConversationKey = searchParams.get("new");
  const [projects, setProjects] = useState<Project[]>([]);
  const [groupProjectId, setGroupProjectId] = useState("");
  const [newLinkedProjectId, setNewLinkedProjectId] = useState("");
  const [senderNames, setSenderNames] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [creatingGroup, setCreatingGroup] = useState(false);

  useEffect(() => {
    const routeAction = selectedConversationId ? `conversation:${selectedConversationId}` : newConversationKey ? `new:${newConversationKey}` : "empty";
    if (lastRouteAction.current === routeAction) return;
    lastRouteAction.current = routeAction;
    if (selectedConversationId) void loadConversation(selectedConversationId);
    else startNewConversation();
  }, [loadConversation, newConversationKey, selectedConversationId, startNewConversation]);

  useEffect(() => {
    if (conversationId && !selectedConversationId) {
      lastRouteAction.current = `conversation:${conversationId}`;
      router.replace(`/chat?conversation=${conversationId}`, { scroll: false });
    }
  }, [conversationId, selectedConversationId, router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    loadWorkspace(user).then((data) => {
      if (cancelled) return;
      setProjects(data.projects);
      setGroupProjectId((current) => data.projects.some((project) => project.id === current) ? current : data.projects[0]?.id ?? "");
    }).catch((err) => { if (!cancelled) setActionError(friendlyErrorMessage(err, "دریافت پروژه‌ها ناموفق بود.")); });
    return () => { cancelled = true; };
  }, [user]);

  const [personalDocs, setPersonalDocs] = useState<Document[]>([]);
  const [projectDocs, setProjectDocs] = useState<Document[]>([]);

  // Load personal documents
  useEffect(() => {
    let cancelled = false;
    documentsApi.listPersonal().then((items) => {
      if (!cancelled) setPersonalDocs(items);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Load active project documents
  const activeProjectId = conversation?.project_id || conversation?.linked_project_id || newLinkedProjectId;
  useEffect(() => {
    if (!activeProjectId) {
      setProjectDocs([]);
      return;
    }
    let cancelled = false;
    documentsApi.list(activeProjectId).then((items) => {
      if (!cancelled) setProjectDocs(items);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [activeProjectId]);

  useEffect(() => {
    if (conversation?.type !== "project_group" || !conversation.project_id) return;
    let cancelled = false;
    workspaceApi.projectMembers(conversation.project_id).then((members) => {
      if (!cancelled) setSenderNames(Object.fromEntries(members.map((member) => [member.user.id, member.user.full_name || member.user.email])));
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [conversation?.type, conversation?.project_id]);

  async function createGroup() {
    if (!groupProjectId) return;
    setCreatingGroup(true);
    setActionError(null);
    try {
      const created = await chatApi.createGroup(groupProjectId);
      window.dispatchEvent(new Event("orbit:conversations-changed"));
      router.push(`/chat?conversation=${created.id}`);
    } catch (err) { setActionError(friendlyErrorMessage(err, "ایجاد گفتگوی گروهی ناموفق بود.")); }
    finally { setCreatingGroup(false); }
  }

  async function changeLinkedProject(projectId: string | null) {
    setActionError(null);
    try { await linkProject(projectId); }
    catch (err) { setActionError(friendlyErrorMessage(err, "اتصال پروژه ناموفق بود.")); }
  }

  async function handleUpload(file: File) {
    let targetId = conversationId;
    if (!targetId) {
      try {
        const created = await chatApi.createPersonal(newLinkedProjectId || null, file.name);
        targetId = created.id;
        void loadConversation(created.id);
        window.dispatchEvent(new Event("orbit:conversations-changed"));
        router.replace(`/chat?conversation=${created.id}`, { scroll: false });
      } catch (err) {
        throw new Error(friendlyErrorMessage(err, "شروع گفتگو برای آپلود سند ناموفق بود."));
      }
    }
    await chatApi.uploadDocument(targetId, file);
    // Save to user's personal documents library as well
    void documentsApi.uploadPersonal(file).then(() => {
      void documentsApi.listPersonal().then(setPersonalDocs).catch(() => {});
    }).catch(() => {});
  }

  const availableDocs = [
    ...personalDocs.map((d) => ({ id: d.id, filename: d.filename, isPersonal: true })),
    ...projectDocs.map((d) => ({ id: d.id, filename: d.filename, isPersonal: false })),
  ];

  return <main className="flex h-full min-h-0 flex-col overflow-hidden bg-white">
    <div className="shrink-0 border-b border-gray-100 px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-2">
        <h1 className="text-sm font-semibold text-gray-800">{conversation?.type === "project_group" ? `گفتگوی گروهی: ${conversation.title}` : "دستیار اسناد سازمان"}</h1>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {conversation?.type !== "project_group" && <>
            <label htmlFor="linked-project" className="text-gray-500">دانش پروژه</label>
            <select id="linked-project" value={conversationId ? conversation?.linked_project_id ?? "" : newLinkedProjectId} onChange={(event) => conversationId ? void changeLinkedProject(event.target.value || null) : setNewLinkedProjectId(event.target.value)} className="rounded-lg border border-gray-200 bg-white p-1.5 text-xs"><option value="">بدون پروژه (آپلود آزاد / عمومی)</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
          </>}
          {conversation?.type !== "project_group" && projects.length > 0 && <>
            <select aria-label="پروژه برای گفتگوی گروهی" value={groupProjectId} onChange={(event) => setGroupProjectId(event.target.value)} className="rounded-lg border border-gray-200 bg-white p-1.5 text-xs">{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
            <button type="button" disabled={creatingGroup} onClick={() => void createGroup()} className="rounded-lg bg-brand-50 px-2 py-1.5 font-medium text-brand-700 disabled:opacity-50">گفتگوی گروهی جدید</button>
          </>}
        </div>
      </div>
      {actionError && <p role="alert" className="mx-auto mt-2 max-w-3xl text-xs text-red-600">{actionError}</p>}
    </div>
    <div className="min-h-0 flex-1"><ChatWindow messages={messages} isStreaming={isStreaming} isLoadingConversation={isLoadingConversation} error={error} onSend={(text) => void sendMessage(text, newLinkedProjectId || null)} group={conversation?.type === "project_group"} senderNames={senderNames} onUpload={handleUpload} availableDocuments={availableDocs} agentStatusText={agentStatusText ?? undefined} /></div>
    <span className="sr-only" aria-live="polite">{conversationId ? "گفتگو انتخاب شده است" : "گفتگوی جدید"}</span>
  </main>;
}
