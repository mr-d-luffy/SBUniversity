"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { BookOpen, Loader2 } from "lucide-react";
import { api, getDevAuthToken } from "@/lib/api";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

type Course = { id: string; code: string; title: string; description?: string | null; enrolled: boolean };
export default function StudentCoursesPage() {
  const { getToken } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const load = useCallback(async () => {
    const token = await getToken() || ((process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development") ? getDevAuthToken("student") : undefined);
    if (!token) return;
    try { setCourses(await api<Course[]>("/student/course-catalog", token)); } catch (e) { setError(e instanceof Error ? e.message : "Could not load courses"); }
  }, [getToken]);
  useEffect(() => { void load(); }, [load]);
  async function enroll(course: Course) {
    setBusy(course.id); setError("");
    try { const token = await getToken() || getDevAuthToken("student"); await api(`/student/courses/${course.id}/enroll`, token, { method: "POST" }); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Enrollment failed"); }
    finally { setBusy(""); }
  }
  return <main className="mx-auto max-w-5xl space-y-6 p-6"><header><h1 className="text-2xl font-bold">Course catalog</h1><p className="text-muted-foreground">Choose a published course to add it to your learning.</p></header>{error && <p role="alert" className="text-red-600">{error}</p>}<div className="grid gap-4 md:grid-cols-2">{courses.map(course => <Card key={course.id} className="space-y-3 p-5"><div className="flex items-center gap-2"><BookOpen size={20}/><span className="text-sm font-medium">{course.code}</span></div><h2 className="text-lg font-semibold">{course.title}</h2><p className="text-sm text-muted-foreground">{course.description || "Explore course lessons and activities."}</p>{course.enrolled ? <Link href={`/student/tasks?course_id=${encodeURIComponent(course.id)}`} className="inline-flex min-h-11 items-center rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white hover:bg-green-800">Open course tasks</Link> : <Button disabled={busy === course.id} onClick={() => void enroll(course)}>{busy === course.id ? <Loader2 className="animate-spin"/> : "Choose course"}</Button>}</Card>)}</div>{!courses.length && <p>No published courses are available yet.</p>}</main>;
}
