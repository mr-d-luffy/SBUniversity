"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "@clerk/nextjs";
import { Loader2, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface TeacherCourse {
  id: string;
  title: string;
  code: string;
}

interface CourseStudent {
  id: string;
  full_name: string;
  email: string;
}

type AssignmentScope = "all_students" | "selected_students";

export function TeacherTaskCreator() {
  const { getToken } = useAuth();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [courses, setCourses] = useState<TeacherCourse[]>([]);
  const [courseId, setCourseId] = useState("");
  const [students, setStudents] = useState<CourseStudent[]>([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([]);
  const [scope, setScope] = useState<AssignmentScope>("all_students");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [points, setPoints] = useState(10);
  const [dueAt, setDueAt] = useState("");
  const [resourceType, setResourceType] = useState<"video" | "learning_source">("video");
  const [resourceUrl, setResourceUrl] = useState("");
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadCourses = useCallback(async () => {
    setLoadingCourses(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const courseOptions = await api<TeacherCourse[]>("/teacher/task-courses", token ?? undefined);
      setCourses(courseOptions);
      setCourseId((current) =>
        courseOptions.some((course) => course.id === current)
          ? current
          : courseOptions[0]?.id ?? ""
      );
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to load courses.");
    } finally {
      setLoadingCourses(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  const loadStudents = useCallback(async () => {
    setLoadingStudents(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const data = await api<CourseStudent[]>("/teacher/task-students", token ?? undefined);
      setStudents(data);
      setSelectedStudentIds((current) =>
        current.filter((id) => data.some((student) => student.id === id))
      );
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to load active students.");
    } finally {
      setLoadingStudents(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    if (scope === "selected_students") void loadStudents();
  }, [loadStudents, scope]);

  function resetForm() {
    setTitle("");
    setDescription("");
    setPoints(10);
    setDueAt("");
    setResourceType("video");
    setResourceUrl("");
    setScope("all_students");
    setSelectedStudentIds([]);
    setLoadError(null);
  }

  async function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!courseId) {
      setLoadError("Choose a course before creating a task.");
      return;
    }
    if (scope === "selected_students" && selectedStudentIds.length === 0) {
      setLoadError("Select at least one student for this task.");
      return;
    }

    setSaving(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      await api("/tasks", token ?? undefined, {
        method: "POST",
        body: JSON.stringify({
          course_id: courseId,
          title: title.trim(),
          description: description.trim() || undefined,
          points,
          due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
          resource_type: resourceType,
          resource_url: resourceUrl.trim(),
          assignment_scope: scope,
          target_student_ids: scope === "selected_students" ? selectedStudentIds : [],
        }),
      });
      toast("Task created and assigned successfully.");
      resetForm();
      setOpen(false);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to create task.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Button variant="primary" size="sm" className="min-h-11" onClick={() => setOpen(true)}>
        <Plus size={15} /> Create Task
      </Button>

      {open && createPortal((
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-2 sm:items-center sm:p-4">
          <button
            type="button"
            aria-label="Close task creator"
            className="absolute inset-0 bg-green-900/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-task-title"
            className="relative my-auto max-h-[calc(100dvh-1rem)] w-full max-w-2xl overflow-y-auto rounded-2xl border border-cream-300 bg-white p-4 shadow-2xl sm:max-h-[90vh] sm:p-6"
          >
            <div className="mb-5 flex items-start justify-between border-b border-cream-200 pb-3">
              <div className="min-w-0">
                <h2 id="create-task-title" className="break-words font-heading text-xl font-bold text-green-900">
                  Create learning task
                </h2>
                <p className="mt-1 text-sm text-ink-muted">
                  Share a video or learning resource with a course or any selected active students.
                </p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setOpen(false)}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-ink-muted hover:bg-cream-100"
              >
                <X size={18} />
              </button>
            </div>

            {loadingCourses ? (
              <div className="flex justify-center py-10">
                <Loader2 className="animate-spin text-green-700" />
              </div>
            ) : courses.length === 0 ? (
              <div className="space-y-3">
                <p className="text-sm text-ink-muted">No courses exist yet.</p>
                {loadError && <p className="text-sm text-danger">{loadError}</p>}
                <Button variant="secondary" size="sm" onClick={() => void loadCourses()}>
                  Retry
                </Button>
              </div>
            ) : (
              <form onSubmit={createTask} className="space-y-4">
                <div className="grid min-w-0 gap-4 sm:grid-cols-2">
                  <label className="block text-sm font-semibold text-green-900">
                    Course
                    <select
                      required
                      value={courseId}
                      onChange={(event) => {
                        setCourseId(event.target.value);
                        setStudents([]);
                        setSelectedStudentIds([]);
                      }}
                      className="mt-1 h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm font-normal text-ink"
                    >
                      {courses.map((course) => (
                        <option key={course.id} value={course.id}>
                          {course.code} · {course.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-semibold text-green-900">
                    Task title
                    <input
                      required
                      maxLength={200}
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      className="mt-1 h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink"
                      placeholder="e.g. Introduction to neural networks"
                    />
                  </label>
                </div>

                <div className="grid min-w-0 gap-4 sm:grid-cols-2">
                  <label className="block text-sm font-semibold text-green-900">
                    Resource format
                    <select
                      value={resourceType}
                      onChange={(event) =>
                        setResourceType(event.target.value as "video" | "learning_source")
                      }
                      className="mt-1 h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm font-normal text-ink"
                    >
                      <option value="video">Video</option>
                      <option value="learning_source">Learning source</option>
                    </select>
                  </label>
                  <label className="block text-sm font-semibold text-green-900">
                    Resource URL
                    <input
                      required
                      type="url"
                      value={resourceUrl}
                      onChange={(event) => setResourceUrl(event.target.value)}
                      className="mt-1 h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink"
                      placeholder={resourceType === "video" ? "https://www.youtube.com/watch?v=..." : "https://..."}
                    />
                    {resourceType === "video" && (
                      <span className="mt-1 block text-xs font-normal text-ink-muted">
                        YouTube videos are tracked; students must watch at least 80% before submitting.
                      </span>
                    )}
                  </label>
                </div>

                <label className="block text-sm font-semibold text-green-900">
                  Instructions
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    className="mt-1 min-w-0 max-w-full w-full rounded-lg border border-cream-300 p-3 text-sm font-normal text-ink"
                    placeholder="What should students learn or submit?"
                  />
                </label>

                <div className="grid min-w-0 gap-4 sm:grid-cols-2">
                  <label className="block text-sm font-semibold text-green-900">
                    Task points
                    <input
                      type="number"
                      min={0}
                      required
                      value={points}
                      onChange={(event) => setPoints(Number(event.target.value))}
                      className="mt-1 h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink"
                    />
                  </label>
                  <label className="block text-sm font-semibold text-green-900">
                    Due date (optional)
                    <input
                      type="datetime-local"
                      value={dueAt}
                      onChange={(event) => setDueAt(event.target.value)}
                      className="mt-1 h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink"
                    />
                  </label>
                </div>

                <fieldset className="space-y-2 rounded-xl border border-cream-300 p-4">
                  <legend className="px-1 text-sm font-semibold text-green-900">
                    Assign task to
                  </legend>
                  <label className="flex min-h-11 items-start gap-2 py-2 text-sm text-ink">
                    <input
                      type="radio"
                      name="assignment-scope"
                      checked={scope === "all_students"}
                      onChange={() => setScope("all_students")}
                    />
                    All active students enrolled in this course
                  </label>
                  <label className="flex min-h-11 items-start gap-2 py-2 text-sm text-ink">
                    <input
                      type="radio"
                      name="assignment-scope"
                      checked={scope === "selected_students"}
                      onChange={() => setScope("selected_students")}
                    />
                    Select specific students
                  </label>

                  {scope === "selected_students" && (
                    <div className="max-h-44 space-y-2 overflow-y-auto border-t border-cream-200 pt-3">
                      {loadingStudents ? (
                        <div className="flex items-center gap-2 text-sm text-ink-muted">
                          <Loader2 size={15} className="animate-spin" /> Loading enrolled students…
                        </div>
                      ) : students.length === 0 ? (
                        <p className="text-sm text-ink-muted">No active students are available.</p>
                      ) : (
                        students.map((student) => (
                          <label key={student.id} className="flex min-h-11 min-w-0 items-start gap-2 py-2 text-sm text-ink">
                            <input
                              type="checkbox"
                              checked={selectedStudentIds.includes(student.id)}
                              onChange={(event) =>
                                setSelectedStudentIds((current) =>
                                  event.target.checked
                                    ? [...current, student.id]
                                    : current.filter((id) => id !== student.id)
                                )
                              }
                            />
                            <span className="shrink-0">{student.full_name}</span>
                            <span className="min-w-0 break-all text-xs text-ink-muted">{student.email}</span>
                          </label>
                        ))
                      )}
                    </div>
                  )}
                </fieldset>

                {loadError && <p role="alert" className="text-sm text-danger">{loadError}</p>}
                <div className="flex flex-col-reverse gap-2 border-t border-cream-200 pt-4 sm:flex-row sm:justify-end sm:gap-3">
                  <Button type="button" variant="secondary" size="sm" className="min-h-11 w-full sm:w-auto" onClick={() => setOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" size="sm" className="min-h-11 w-full sm:w-auto" disabled={saving || loadingStudents}>
                    {saving ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
                    Create and assign
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      ), document.body)}
    </>
  );
}
