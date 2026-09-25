"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, workspaceApi } from "@/shared/lib/workspaceApi";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Modal } from "@/shared/components/ui/Modal";
import { OrbitIcon } from "@/shared/components/ui/OrbitIcon";
import { Select } from "@/shared/components/ui/Select";
import { Project } from "@/shared/types";
import { Document } from "@/features/documents/types";
import { documentsApi } from "@/features/documents/api/documentsApi";
import { chatApi } from "../api/chatApi";
import { ChatWindow } from "../components/ChatWindow";
import { useChat } from "../hooks/useChat";

export function ChatScreen() {
  const { conversation, conversationId, messages, conversationDocuments, hasProcessingDocuments, isStreaming, isSending, agentActivities, connectionState, isLoadingConversation, error, sendMessage, loadConversation, startNewConversation, linkProject, renameConversation, stopResponse, registerDocument } = useChat();
  const user = useAuthStore((state) => state.user);
  const router = useRouter();
  const searchParams = useSearchParams();
  const lastRouteAction = useRef<string | null>(null);
  const [composerKey, setComposerKey] = useState("initial");
  const selectedConversationId = searchParams.get("conversation");
  const newConversationKey = searchParams.get("new");
  const [projects, setProjects] = useState<Project[]>([]);
  const [groupProjectId, setGroupProjectId] = useState("");
  const [newLinkedProjectId, setNewLinkedProjectId] = useState("");
  const [senderNames, setSenderNames] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);

  const [groupTitle, setGroupTitle] = useState("");
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [titleModalOpen, setTitleModalOpen] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [savingTitle, setSavingTitle] = useState(false);
  const [linkingProject, setLinkingProject] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const closeGroupModal = useCallback(() => { if (!creatingGroup) setGroupModalOpen(false); }, [creatingGroup]);
  const closeTitleModal = useCallback(() => { if (!savingTitle) setTitleModalOpen(false); }, [savingTitle]);

  useEffect(() => {
    const routeAction = selectedConversationId ? `conversation:${selectedConversationId}` : newConversationKey ? `new:${newConversationKey}` : "empty";
    if (lastRouteAction.current !== routeAction) {
      lastRouteAction.current = routeAction;
      setComposerKey(routeAction);
      setGroupModalOpen(false);
      setTitleModalOpen(false);
      setActionError(null);
      if (selectedConversationId) void loadConversation(selectedConversationId);
      else startNewConversation();
      return;
    }
    if (conversationId && !selectedConversationId) {
      lastRouteAction.current = `conversation:${conversationId}`;
      router.replace(`/chat?conversation=${conversationId}`, { scroll: false });
    }
  }, [conversationId, loadConversation, newConversationKey, selectedConversationId, startNewConversation, router]);

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
  const activeProjectId = conversationId ? conversation?.project_id || conversation?.linked_project_id : newLinkedProjectId;
  const [loadedDocsProjectId, setLoadedDocsProjectId] = useState("");
  useEffect(() => {
    if (!activeProjectId) {
      return;
    }
    let cancelled = false;
    documentsApi.list(activeProjectId).then((items) => {
      if (!cancelled) { setProjectDocs(items); setLoadedDocsProjectId(activeProjectId); }
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
    setModalError(null);
    try {
      const created = await chatApi.createGroup(groupProjectId, groupTitle);
      window.dispatchEvent(new Event("orbit:conversations-changed"));
      setGroupModalOpen(false);
      setGroupTitle("");
      router.push(`/chat?conversation=${created.id}`);
    } catch (err) { setModalError(friendlyErrorMessage(err, "ایجاد گفتگوی گروهی ناموفق بود.")); }
    finally { setCreatingGroup(false); }
  }

  async function changeLinkedProject(projectId: string | null) {
    setActionError(null);
    setLinkingProject(true);
    try { await linkProject(projectId); }
    catch (err) { setActionError(friendlyErrorMessage(err, "اتصال پروژه ناموفق بود.")); }
    finally { setLinkingProject(false); }
  }

  async function uploadDocument(file: File): Promise<Document> {
    let targetId = conversationId;
    if (!targetId) {
      try {
        const created = await chatApi.createPersonal(newLinkedProjectId || null, file.name);
        targetId = created.id;
        await loadConversation(created.id);
        window.dispatchEvent(new Event("orbit:conversations-changed"));
      } catch (err) {
        throw new Error(friendlyErrorMessage(err, "شروع گفتگو برای آپلود سند ناموفق بود."));
      }
    }
    const result = await chatApi.uploadDocument(targetId, file);
    registerDocument(result.document);
    return result.document;
  }

  async function handleUpload(file: File): Promise<Document> {
    setIsUploadingDocument(true);
    try { return await uploadDocument(file); }
    finally { setIsUploadingDocument(false); }
  }

  const availableDocs = [
    ...conversationDocuments.map((d) => ({ id: d.id, filename: d.filename, isPersonal: false })),
    ...personalDocs.map((d) => ({ id: d.id, filename: d.filename, isPersonal: true })),
    ...(activeProjectId === loadedDocsProjectId ? projectDocs : []).map((d) => ({ id: d.id, filename: d.filename, isPersonal: false })),
  ];

  async function saveTitle() {
    if (!titleDraft.trim() || savingTitle) return;
    setSavingTitle(true);
    setModalError(null);
    try { await renameConversation(titleDraft); setTitleModalOpen(false); }
    catch (err) { setModalError(friendlyErrorMessage(err, "ذخیرهٔ عنوان ناموفق بود.")); }
    finally { setSavingTitle(false); }
  }

  const group = conversation?.type === "project_group";
  const projectName = projects.find((project) => project.id === activeProjectId)?.name;

  return <main className="chat-surface flex h-full min-h-0 flex-col overflow-hidden">
    <header className="shrink-0 border-b border-slate-200/70 bg-white/80 px-4 py-4 backdrop-blur-xl sm:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white text-brand-700"><OrbitIcon name={group ? "people" : "spark"} /></span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="max-w-[min(55vw,380px)] truncate text-sm font-bold text-slate-800">{conversation?.title || "دستیار هوشمند"}</h1>
              {conversation && <button type="button" disabled={isStreaming || linkingProject || isUploadingDocument} aria-label="ویرایش عنوان گفتگو" title="ویرایش عنوان گفتگو" onClick={() => { setTitleDraft(conversation.title); setModalError(null); setTitleModalOpen(true); }} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-brand-700 disabled:opacity-40"><OrbitIcon name="edit" className="h-3.5 w-3.5" /></button>}
            </div>
            <p className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
              <span className={`h-1.5 w-1.5 rounded-full ${group && connectionState !== "connected" ? "bg-amber-500" : "bg-teal-500"}`} />
              {group ? `${projectName || "گفتگوی پروژه"} · ${connectionState === "connected" ? "متصل" : connectionState === "reconnecting" ? "در حال اتصال مجدد…" : "در حال اتصال…"}` : "همراه شما در دانش سازمان"}
            </p>
          </div>
        </div>
        <button type="button" onClick={() => { setModalError(null); setGroupModalOpen(true); }} disabled={isLoadingConversation || isStreaming || isUploadingDocument} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:border-teal-300 hover:text-teal-700 disabled:opacity-40"><OrbitIcon name="people" className="h-4 w-4" />گفتگوی گروهی جدید</button>
      </div>
    </header>
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200/50 px-4 py-2.5 text-xs sm:px-8">
      <OrbitIcon name="folder" className="h-4 w-4 text-slate-400" />
      {group ? <span className="text-slate-500">دانش پروژه: <span className="font-medium text-slate-700">{projectName || "پروژهٔ این گفتگو"}</span></span> : <>
        <label htmlFor="linked-project" className="text-slate-500">محدودهٔ دانش</label>
        <Select id="linked-project" size="sm" disabled={isLoadingConversation || isStreaming || linkingProject || isUploadingDocument || Boolean(conversationId && !conversation)} value={conversationId ? conversation?.linked_project_id ?? "" : newLinkedProjectId} onChange={(event) => conversationId ? void changeLinkedProject(event.target.value || null) : setNewLinkedProjectId(event.target.value)} className="max-w-[65vw] border-slate-200 font-medium"><option value="">دانش عمومی و اسناد شخصی</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</Select>
      </>}
      <span className="mr-auto hidden text-[11px] text-slate-400 sm:block">پاسخ‌های مستند، تصمیم‌های روشن‌تر</span>
    </div>
    {actionError && <p role="alert" className="mx-4 mt-3 rounded-xl bg-red-50 p-3 text-xs text-red-700">{actionError}</p>}
    <div className="min-h-0 flex-1"><ChatWindow key={composerKey} messages={messages} isStreaming={isStreaming} isSending={isSending} isUploadingDocument={isUploadingDocument} isDocumentProcessing={hasProcessingDocuments} conversationDocuments={conversationDocuments} isLoadingConversation={isLoadingConversation || linkingProject} error={error} onSend={(text) => void sendMessage(text, newLinkedProjectId || null)} group={group} senderNames={senderNames} onUpload={handleUpload} availableDocuments={availableDocs} agentActivities={agentActivities} onStop={stopResponse} userName={user?.full_name?.split(" ")[0]} /></div>
    <Modal isOpen={groupModalOpen} onClose={closeGroupModal} title="یک گفتگو برای تیم شما">
      <p className="mb-5 text-sm leading-7 text-slate-500">دربارهٔ پروژه گفتگو کنید و با منشن کردن دستیار، از دانش و اسناد پروژه کمک بگیرید.</p>
      <form onSubmit={(event) => { event.preventDefault(); void createGroup(); }} className="space-y-4">
        <div><label htmlFor="group-project" className="mb-2 block text-sm font-medium text-slate-700">پروژه</label><Select id="group-project" required disabled={creatingGroup} value={groupProjectId} onChange={(event) => setGroupProjectId(event.target.value)}>{projects.length === 0 && <option value="">پروژه‌ای در دسترس نیست</option>}{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</Select></div>
        <Input label="عنوان گفتگو (اختیاری)" value={groupTitle} disabled={creatingGroup} onChange={(event) => setGroupTitle(event.target.value)} placeholder="مثلاً برنامه‌ریزی اسپرینت جدید" />
        <p className="text-xs leading-6 text-slate-500">اگر عنوان خالی باشد، نام پیش‌فرض گفتگو انتخاب می‌شود.</p>
        {modalError && <p role="alert" className="text-xs leading-6 text-red-600">{modalError}</p>}
        <div className="flex justify-end gap-2 pt-2"><Button type="button" variant="ghost" disabled={creatingGroup} onClick={closeGroupModal}>انصراف</Button><Button type="submit" disabled={!groupProjectId} isLoading={creatingGroup}>ساخت گفتگو<OrbitIcon name="arrow" className="h-4 w-4" /></Button></div>
      </form>
    </Modal>
    <Modal isOpen={titleModalOpen} onClose={closeTitleModal} title="ویرایش عنوان گفتگو">
      <form onSubmit={(event) => { event.preventDefault(); void saveTitle(); }} className="space-y-4">
        <Input label="عنوان گفتگو" value={titleDraft} disabled={savingTitle} onChange={(event) => setTitleDraft(event.target.value)} required />
        {modalError && <p role="alert" className="text-xs leading-6 text-red-600">{modalError}</p>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={savingTitle} onClick={closeTitleModal}>انصراف</Button><Button type="submit" disabled={!titleDraft.trim()} isLoading={savingTitle}>ذخیرهٔ عنوان</Button></div>
      </form>
    </Modal>
  </main>;
}
