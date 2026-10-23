"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "@clerk/nextjs";
import { BookOpen, CalendarDays, ChevronDown, ChevronUp, Loader2, Pencil, RefreshCw, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface TeacherTask {
  id: string;
  course_id: string;
  course_title?: string | null;
  title: string;
  description?: string | null;
  due_at?: string | null;
  points: number;
  resource_type?: "video" | "learning_source" | null;
  resource_url?: string | null;
  assignment_scope: "all_students" | "selected_students";
  target_student_ids?: string[] | null;
  status: "active" | "archived";
  type: "exam" | "assignment";
}

interface CourseStudent {
  id: string;
  full_name: string;
  email: string;
}
interface TeacherCourse {
  id: string;
  title: string;
  code: string;
}

function toDateTimeInput(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

export function TeacherTaskManager() {
  const { getToken } = useAuth();
  const toast = useToast();
  const [tasks, setTasks] = useState<TeacherTask[]>([]);
  const [collapsedCourses, setCollapsedCourses] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [editing, setEditing] = useState<TeacherTask | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [points, setPoints] = useState(0);
  const [resourceType, setResourceType] = useState<"video" | "learning_source" | "">("");
  const [resourceUrl, setResourceUrl] = useState("");
  const [assignmentScope, setAssignmentScope] = useState<"all_students" | "selected_students">("all_students");
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([]);
  const [courses, setCourses] = useState<TeacherCourse[]>([]);
  const [courseId, setCourseId] = useState("");
  const [loadingCourses, setLoadingCourses] = useState(false);
  const [students, setStudents] = useState<CourseStudent[]>([]);
  const [studentsLoaded, setStudentsLoaded] = useState(false);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [studentError, setStudentError] = useState("");
  const [saving, setSaving] = useState(false);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const token = await resolveToken();
      setTasks(await api<TeacherTask[]>("/tasks", token ?? undefined));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Could not load course tasks.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  const loadStudents = useCallback(async () => {
    setLoadingStudents(true);
    setStudentError("");
    setStudentsLoaded(false);
    try {
      const token = await resolveToken();
      setStudents(await api<CourseStudent[]>("/teacher/task-students", token ?? undefined));
      setStudentsLoaded(true);
    } catch (error) {
      setStudentError(error instanceof Error ? error.message : "Could not load active students.");
    } finally {
      setLoadingStudents(false);
    }
  }, [resolveToken]);

  const loadCourses = useCallback(async () => {
    setLoadingCourses(true);
    try {
      const token = await resolveToken();
      setCourses(await api<TeacherCourse[]>("/teacher/task-courses", token ?? undefined));
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not load your courses.");
    } finally {
      setLoadingCourses(false);
    }
  }, [resolveToken, toast]);

  useEffect(() => { void loadTasks(); }, [loadTasks]);
  useEffect(() => {
    if (editing?.type === "assignment") void loadCourses();
  }, [editing?.id, editing?.type, loadCourses]);

  const openEditor = (task: TeacherTask) => {
    setEditing(task);
    setCourseId(task.course_id);
    setTitle(task.title);
    setDescription(task.description ?? "");
    setDueAt(toDateTimeInput(task.due_at));
    setPoints(task.points);
    setResourceType(task.resource_type ?? "");
    setResourceUrl(task.resource_url ?? "");
    setAssignmentScope(task.assignment_scope ?? "all_students");
    setSelectedStudentIds(task.target_student_ids ?? []);
    setStudents([]);
    setStudentsLoaded(false);
    setStudentError("");
  };

  useEffect(() => {
    if (editing?.type === "assignment" && assignmentScope === "selected_students") void loadStudents();
  }, [assignmentScope, editing?.id, editing?.type, loadStudents]);

  const saveTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    try {
      const token = await resolveToken();
      const updated = await api<TeacherTask>(`/tasks/${editing.id}`, token ?? undefined, {
        method: "PATCH",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim() || null,
          points,
          due_at: dueAt ? new Date(dueAt).toISOString() : null,
          ...(editing.type === "assignment" ? {
            ...(courseId !== editing.course_id ? { course_id: courseId } : {}),
            resource_type: resourceType || null,
            resource_url: resourceType ? resourceUrl.trim() : null,
            assignment_scope: assignmentScope,
            target_student_ids: assignmentScope === "selected_students" ? selectedStudentIds : [],
          } : {}),
        }),
      });
      setTasks((current) => current.map((task) => task.id === updated.id ? { ...task, ...updated } : task));
      toast(`Updated “${updated.title}”.`);
      setEditing(null);
      void loadTasks();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not update this task.");
    } finally {
      setSaving(false);
    }
  };

  const groups = Object.values(tasks.reduce<Record<string, { id: string; title: string; tasks: TeacherTask[] }>>((result, task) => {
    const id = task.course_id || "unassigned";
    if (!result[id]) result[id] = { id, title: task.course_title || "Other Tasks", tasks: [] };
    result[id].tasks.push(task);
    return result;
  }, {})).sort((a, b) => a.title.localeCompare(b.title));

  return (
    <section className="mt-6 space-y-4" aria-labelledby="teacher-task-manager-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="teacher-task-manager-title" className="font-heading text-xl font-bold text-green-900">Manage Course Tasks</h2>
          <p className="mt-1 text-sm text-ink-muted">Update course, task details, points, learning resources, assignment scope, students, and due dates.</p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={() => void loadTasks()} disabled={loading}>
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
        </Button>
      </div>

      <div className="space-y-4">
      {loading ? (
        <div className="flex h-36 items-center justify-center rounded-2xl border border-cream-300 bg-white"><Loader2 className="h-6 w-6 animate-spin text-green-700" /></div>
      ) : loadError ? (
        <Card className="p-5 text-center">
          <p role="alert" className="text-sm text-danger">{loadError}</p>
          <Button type="button" variant="secondary" size="sm" className="mt-3" onClick={() => void loadTasks()}>Try again</Button>
        </Card>
      ) : groups.length === 0 ? (
        <Card className="p-6 text-center text-sm text-ink-muted">No course tasks are available to manage yet.</Card>
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <section key={group.id} aria-label={`${group.title} tasks`}>
              <div className="mb-3 flex items-center gap-2 border-b border-cream-300 pb-2">
                <BookOpen size={17} className="text-green-700" />
                <h3 className="font-heading text-base font-bold text-green-900">{group.title}</h3>
                <span className="text-xs text-ink-muted">{group.tasks.length} task{group.tasks.length === 1 ? "" : "s"}</span>
                <button
                  type="button"
                  className="ml-auto inline-flex min-h-9 items-center gap-1 rounded-lg px-2 text-xs font-semibold text-green-800 hover:bg-green-50"
                  aria-expanded={!collapsedCourses[group.id]}
                  aria-controls={`course-tasks-${group.id}`}
                  onClick={() => setCollapsedCourses((current) => ({ ...current, [group.id]: !current[group.id] }))}
                >
                  {collapsedCourses[group.id] ? <><ChevronDown size={14} /> Show tasks</> : <><ChevronUp size={14} /> Hide tasks</>}
                </button>
              </div>
              {!collapsedCourses[group.id] && <div id={`course-tasks-${group.id}`} className="grid gap-3 md:grid-cols-2">
                {group.tasks.map((task) => (
                  <Card key={task.id} className="flex min-w-0 items-start justify-between gap-3 p-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="break-words font-semibold text-green-900">{task.title}</h4>
                        <Badge tone={task.status === "active" ? "success" : "neutral"}>{task.status === "active" ? "Active" : "Archived"}</Badge>
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs text-ink-muted">{task.description || "No instructions provided."}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-muted">
                        <span>{task.points} points · {task.type === "exam" ? "Exam task" : "Assignment"}</span>
                        <span className="inline-flex items-center gap-1"><CalendarDays size={12} />{task.due_at ? new Date(task.due_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "No due date"}</span>
                        {task.type === "assignment" && <span>{task.assignment_scope === "selected_students" ? `${task.target_student_ids?.length ?? 0} selected students` : "All course students"}</span>}
                      </div>
                    </div>
                    <Button type="button" variant="secondary" size="sm" className="shrink-0" onClick={() => openEditor(task)}>
                      <Pencil size={14} /> Edit
                    </Button>
                  </Card>
                ))}
              </div>}
            </section>
          ))}
        </div>
      )}
      </div>

      {editing && createPortal(
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-3 sm:items-center sm:p-4">
          <button type="button" aria-label="Close task editor" className="absolute inset-0 bg-green-900/50 backdrop-blur-sm" onClick={() => setEditing(null)} />
          <div role="dialog" aria-modal="true" aria-labelledby="edit-teacher-task-title" className="relative my-auto max-h-[calc(100dvh-1.5rem)] w-full max-w-xl overflow-y-auto rounded-2xl border border-cream-300 bg-white p-4 shadow-2xl sm:p-6">
            <div className="mb-4 flex items-start justify-between gap-3 border-b border-cream-200 pb-3">
              <div className="min-w-0">
                <h3 id="edit-teacher-task-title" className="font-heading text-lg font-bold text-green-900">Edit course task</h3>
                <p className="mt-1 text-xs text-ink-muted">{editing.course_title || "Course"}</p>
              </div>
              <button type="button" aria-label="Close" className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-ink-muted hover:bg-cream-100" onClick={() => setEditing(null)}><X size={18} /></button>
            </div>
            <form onSubmit={saveTask} className="space-y-4">
              {editing.type === "assignment" && <label className="block text-sm font-semibold text-green-900">Course
                <select required disabled={loadingCourses} value={courseId} onChange={(event) => setCourseId(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-cream-300 bg-white px-3 text-sm font-normal text-ink disabled:bg-cream-50">
                  {!courses.some((course) => course.id === editing.course_id) && <option value={editing.course_id}>{editing.course_title || "Current course"} (not currently assigned)</option>}
                  {courses.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}
                </select>
                <span className="mt-1 block text-[11px] font-normal text-ink-muted">Only courses assigned to you can be selected.</span>
              </label>}
              <label className="block text-sm font-semibold text-green-900">Task title
                <input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink" />
              </label>
              <label className="block text-sm font-semibold text-green-900">Instructions
                <textarea rows={4} value={description} onChange={(event) => setDescription(event.target.value)} className="mt-1 w-full rounded-lg border border-cream-300 p-3 text-sm font-normal text-ink" placeholder="What should students learn or submit?" />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-semibold text-green-900">Task points
                  <input type="number" min={0} required value={points} onChange={(event) => setPoints(Number(event.target.value))} className="mt-1 h-11 w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink" />
                  <span className="mt-1 block text-[11px] font-normal text-ink-muted">Previously awarded points remain unchanged.</span>
                </label>
                <label className="block text-sm font-semibold text-green-900">Due date (optional)
                  <input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink" />
                </label>
              </div>
              {editing.type === "assignment" ? (
                <>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="block text-sm font-semibold text-green-900">Resource format
                      <select value={resourceType} onChange={(event) => setResourceType(event.target.value as "video" | "learning_source" | "")} className="mt-1 h-11 w-full rounded-lg border border-cream-300 bg-white px-3 text-sm font-normal text-ink">
                        <option value="">No resource</option><option value="video">YouTube video</option><option value="learning_source">Learning source</option>
                      </select>
                    </label>
                    <label className="block text-sm font-semibold text-green-900">Resource URL
                      <input type="url" required={Boolean(resourceType)} disabled={!resourceType} value={resourceUrl} onChange={(event) => setResourceUrl(event.target.value)} className="mt-1 h-11 w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink disabled:bg-cream-50" placeholder={resourceType === "video" ? "https://youtube.com/watch?v=..." : "https://..."} />
                    </label>
                  </div>
                  {resourceType === "video" && <p className="-mt-2 text-xs text-ink-muted">Changing the video resets saved student watch progress.</p>}
                  <fieldset className="space-y-2 rounded-xl border border-cream-200 p-3">
                    <legend className="px-1 text-sm font-semibold text-green-900">Assign to</legend>
                    <label className="flex min-h-9 items-center gap-2 text-sm text-ink"><input type="radio" checked={assignmentScope === "all_students"} onChange={() => setAssignmentScope("all_students")} />All students in this course</label>
                    <label className="flex min-h-9 items-center gap-2 text-sm text-ink"><input type="radio" checked={assignmentScope === "selected_students"} onChange={() => setAssignmentScope("selected_students")} />Selected students</label>
                    {assignmentScope === "selected_students" && (
                      <div className="max-h-40 space-y-1 overflow-y-auto border-t border-cream-200 pt-2">
                        {loadingStudents ? <p className="flex items-center gap-2 py-2 text-xs text-ink-muted"><Loader2 size={14} className="animate-spin" />Loading active students…</p> : studentError ? <p role="alert" className="py-2 text-xs text-danger">{studentError} <button type="button" className="font-semibold underline" onClick={() => void loadStudents()}>Retry</button></p> : students.map((student) => (
                          <label key={student.id} className="flex min-h-9 items-center gap-2 text-xs text-ink">
                            <input type="checkbox" checked={selectedStudentIds.includes(student.id)} onChange={(event) => setSelectedStudentIds((current) => event.target.checked ? [...current, student.id] : current.filter((id) => id !== student.id))} />
                            <span className="font-medium">{student.full_name}</span><span className="truncate text-ink-muted">{student.email}</span>
                          </label>
                        ))}
                        {!loadingStudents && !studentError && selectedStudentIds.filter((id) => !students.some((student) => student.id === id)).map((id) => (
                          <label key={id} className="flex min-h-9 items-center gap-2 text-xs text-ink-muted">
                            <input type="checkbox" checked onChange={() => setSelectedStudentIds((current) => current.filter((studentId) => studentId !== id))} />
                            <span>Previously assigned student unavailable ({id.slice(0, 8)})</span>
                          </label>
                        ))}
                        {!loadingStudents && !studentError && students.length === 0 && <p className="py-2 text-xs text-ink-muted">No active students found.</p>}
                      </div>
                    )}
                  </fieldset>
                  {assignmentScope === "selected_students" && selectedStudentIds.length === 0 && <p className="text-xs text-warning">Choose at least one student.</p>}
                </>
              ) : (
                <p className="rounded-lg bg-cream-50 p-3 text-xs text-ink-muted">This task is linked to an exam. Edit the exam’s resource and assignment settings from Exam Management.</p>
              )}
              <div className="flex flex-col-reverse gap-2 border-t border-cream-200 pt-4 sm:flex-row sm:justify-end">
                <Button type="button" variant="secondary" size="sm" className="min-h-11" onClick={() => setEditing(null)}>Cancel</Button>
                <Button type="submit" variant="primary" size="sm" className="min-h-11" disabled={saving || loadingCourses || loadingStudents || (editing.type === "assignment" && assignmentScope === "selected_students" && (!studentsLoaded || selectedStudentIds.length === 0))}>
                  {saving ? <Loader2 size={15} className="animate-spin" /> : <Pencil size={14} />} Save changes
                </Button>
              </div>
            </form>
          </div>
        </div>, document.body
      )}
    </section>
  );
}
