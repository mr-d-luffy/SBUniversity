"use client";

import { FormEvent, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { api, getDevAuthToken } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function NewTeacherCoursePage() {
  const { getToken } = useAuth(); const router = useRouter();
  const [code, setCode] = useState(""); const [title, setTitle] = useState(""); const [description, setDescription] = useState("");
  const [published, setPublished] = useState(true); const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try { const token = await getToken() || getDevAuthToken("teacher"); await api("/teacher/courses", token, { method: "POST", body: JSON.stringify({ code, title, description: description || null, is_published: published }) }); router.push("/teacher/dashboard"); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create course"); }
    finally { setSaving(false); }
  }
  return <main className="mx-auto max-w-2xl space-y-6 p-6"><header><h1 className="text-2xl font-bold">Create a course</h1><p className="text-muted-foreground">Set up a course for your students.</p></header><Card className="p-6"><form className="space-y-4" onSubmit={submit}><label className="block space-y-1">Course code<input required maxLength={50} value={code} onChange={e => setCode(e.target.value)} className="w-full rounded-md border p-2" placeholder="BIO101"/></label><label className="block space-y-1">Course name<input required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} className="w-full rounded-md border p-2" placeholder="Introduction to Biology"/></label><label className="block space-y-1">Description<textarea value={description} onChange={e => setDescription(e.target.value)} className="w-full rounded-md border p-2" rows={4}/></label><label className="flex items-center gap-2"><input type="checkbox" checked={published} onChange={e => setPublished(e.target.checked)}/> Publish course so students can choose it</label>{error && <p role="alert" className="text-red-600">{error}</p>}<Button type="submit" disabled={saving}>{saving ? "Creating…" : "Create course"}</Button></form></Card></main>;
}
