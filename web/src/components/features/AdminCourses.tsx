"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "@clerk/nextjs";
import { BookOpen, Loader2, Pencil, Plus, Trash2, Users, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface AdminCourse {
  id: string;
  code: string;
  title: string;
  teacher_id: string;
  teacher_ids: string[];
  student_ids: string[];
  description?: string | null;
  is_published: boolean;
  enrolled_students: number;
}

type CreateCourseResponse = AdminCourse;

interface TeacherOption {
  id: string;
  full_name: string;
  email: string;
}

interface StudentOption {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
}

function defaultCourseCode() {
  return `OU-${new Date().getFullYear()}-01`;
}

export function AdminCourses() {
  const { getToken } = useAuth();
  const toast = useToast();
  const [courses, setCourses] = useState<AdminCourse[]>([]);
  const [teachers, setTeachers] = useState<TeacherOption[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<AdminCourse | null>(null);
  const [deletingCourse, setDeletingCourse] = useState<AdminCourse | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [code, setCode] = useState(defaultCourseCode);
  const [title, setTitle] = useState("OpenUniversity Course");
  const [description, setDescription] = useState("");
  const [enrollAll, setEnrollAll] = useState(true);
  const [isPublished, setIsPublished] = useState(true);
  const [teacherIds, setTeacherIds] = useState<string[]>([]);
  const [studentIds, setStudentIds] = useState<string[]>([]);
  const [studentSearch, setStudentSearch] = useState("");

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("admin");
    }
    return token;
  }, [getToken]);

  const loadCourses = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const [loadedCourses, loadedTeachers, loadedStudents] = await Promise.all([
        api<AdminCourse[]>("/admin/courses", token ?? undefined),
        api<TeacherOption[]>("/admin/courses/teachers", token ?? undefined),
        api<StudentOption[]>("/admin/courses/students", token ?? undefined),
      ]);
      setCourses(loadedCourses);
      setTeachers(loadedTeachers);
      setStudents(loadedStudents);
      setTeacherIds((current) => current.length ? current : loadedTeachers[0] ? [loadedTeachers[0].id] : []);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to load courses.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  function openCreateForm() {
    setEditingCourse(null);
    setCode(defaultCourseCode());
    setTitle("OpenUniversity Course");
    setDescription("");
    setEnrollAll(true);
    setIsPublished(true);
    setTeacherIds(teachers[0] ? [teachers[0].id] : []);
    setStudentIds([]);
    setStudentSearch("");
    setLoadError(null);
    setIsOpen(true);
  }

  function openEditForm(course: AdminCourse) {
    setEditingCourse(course);
    setCode(course.code);
    setTitle(course.title);
    setDescription(course.description ?? "");
    const assignedTeachers = course.teacher_ids.filter((id) => teachers.some((teacher) => teacher.id === id));
    setTeacherIds(assignedTeachers.length ? assignedTeachers : teachers[0] ? [teachers[0].id] : []);
    setStudentIds(course.student_ids);
    setIsPublished(course.is_published);
    setEnrollAll(false);
    setStudentSearch("");
    setLoadError(null);
    setIsOpen(true);
  }

  async function saveCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const payload = {
        code: code.trim(),
        title: title.trim(),
        description: description.trim() || null,
        teacher_ids: teacherIds,
        student_ids: studentIds,
        is_published: isPublished,
        enroll_all_active_students: enrollAll,
      };
      const saved = await api<CreateCourseResponse>(
        editingCourse ? `/admin/courses/${editingCourse.id}` : "/admin/courses",
        token ?? undefined,
        {
          method: editingCourse ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        },
      );
      setCourses((current) => editingCourse
        ? current.map((course) => course.id === saved.id ? saved : course)
        : [saved, ...current]);
      toast(editingCourse
        ? `Updated ${saved.title}.`
        : `Created ${saved.title} and enrolled ${saved.enrolled_students} active student${saved.enrolled_students === 1 ? "" : "s"}.`);
      setIsOpen(false);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to save course.");
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteCourse(course: AdminCourse) {
    setIsDeleting(true);
    try {
      const token = await resolveToken();
      await api(`/admin/courses/${course.id}`, token ?? undefined, { method: "DELETE" });
      setCourses((current) => current.filter((item) => item.id !== course.id));
      if (editingCourse?.id === course.id) {
        setEditingCourse(null);
        setIsOpen(false);
      }
      toast(`Permanently deleted ${course.title} and its related course records.`);
      setDeletingCourse(null);
    } catch (error) {
      toast(error instanceof Error ? error.message : "Failed to delete course.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <div className="mb-6 flex justify-end">
        <Button variant="primary" className="w-full justify-center sm:w-auto" onClick={openCreateForm}>
          <Plus size={16} /> Create OpenUniversity Course
        </Button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center rounded-2xl border border-cream-300 bg-white">
          <Loader2 className="h-7 w-7 animate-spin text-green-700" />
        </div>
      ) : loadError && courses.length === 0 ? (
        <Card className="p-8 text-center">
          <p role="alert" className="text-sm text-danger">{loadError}</p>
          <Button variant="secondary" size="sm" className="mt-4" onClick={() => void loadCourses()}>
            Retry
          </Button>
        </Card>
      ) : courses.length === 0 ? (
        <Card className="p-10 text-center">
          <BookOpen className="mx-auto h-10 w-10 text-cream-400" />
          <h2 className="mt-3 font-heading text-lg font-bold text-green-900">No courses yet</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Create an OpenUniversity course and enroll all active students with one action.
          </p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {courses.map((course) => (
            <Card key={course.id} className="min-w-0 p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wide text-green-700">{course.code}</p>
                  <h2 className="mt-1 break-words font-heading text-lg font-bold text-green-900">{course.title}</h2>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
                  course.is_published ? "bg-green-100 text-green-800" : "bg-cream-200 text-ink-muted"
                }`}>
                  {course.is_published ? "Published" : "Draft"}
                </span>
              </div>
              {course.description && (
                <p className="mt-3 line-clamp-3 text-sm text-ink-muted">{course.description}</p>
              )}
              <div className="mt-5 flex min-w-0 items-start gap-2 border-t border-cream-200 pt-4 text-sm text-ink-muted">
                <Users size={16} className="text-green-700" />
                <span className="break-words">{course.enrolled_students} active student{course.enrolled_students === 1 ? "" : "s"} enrolled</span>
              </div>
              <div className="mt-4 border-t border-cream-200 pt-4">
                <p className="text-xs font-semibold text-green-900">Assigned teachers</p>
                <p className="mt-1 text-sm text-ink-muted">
                  {(course.teacher_ids.length ? course.teacher_ids : [course.teacher_id])
                    .map((id) => teachers.find((teacher) => teacher.id === id)?.full_name)
                    .filter(Boolean)
                    .join(", ") || "Teacher account unavailable"}
                </p>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary" className="min-h-10 flex-1 justify-center gap-1.5" onClick={() => openEditForm(course)}>
                    <Pencil size={14} /> Edit
                  </Button>
                  <Button size="sm" variant="danger" className="min-h-10 flex-1 justify-center gap-1.5" onClick={() => setDeletingCourse(course)}>
                    <Trash2 size={14} /> Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {loadError && courses.length > 0 && (
        <p role="alert" className="mt-4 text-sm text-danger">{loadError}</p>
      )}

      {isOpen && createPortal((
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-3 sm:items-center sm:p-4">
          <button
            type="button"
            aria-label="Close course creator"
            className="absolute inset-0 bg-green-900/50 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="course-form-title"
            className="relative my-auto max-h-[calc(100dvh-1.5rem)] w-full max-w-xl overflow-y-auto rounded-2xl border border-cream-300 bg-white p-4 shadow-2xl sm:max-h-[calc(100dvh-2rem)] sm:p-6"
          >
            <div className="mb-5 flex items-start justify-between border-b border-cream-200 pb-3">
              <div>
                <h2 id="course-form-title" className="font-heading text-xl font-bold text-green-900">
                  {editingCourse ? "Update course" : "Create OpenUniversity Course"}
                </h2>
                <p className="mt-1 text-sm text-ink-muted">
                  Set the course details, assign teachers, and enroll students.
                </p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setIsOpen(false)}
                className="grid min-h-11 min-w-11 shrink-0 place-items-center rounded-lg text-ink-muted hover:bg-cream-100"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={saveCourse} className="space-y-4">
              <fieldset className="rounded-xl border border-cream-300 p-3">
                <legend className="px-1 text-sm font-semibold text-green-900">Assign teachers</legend>
                <div className="max-h-36 space-y-1 overflow-y-auto">
                  {teachers.map((teacher) => (
                    <label key={teacher.id} className="flex min-h-10 items-center gap-2 rounded-lg px-2 text-sm text-ink hover:bg-cream-50">
                      <input
                        type="checkbox"
                        checked={teacherIds.includes(teacher.id)}
                        onChange={() => setTeacherIds((current) => current.includes(teacher.id)
                          ? current.filter((id) => id !== teacher.id)
                          : [...current, teacher.id])}
                      />
                      <span className="min-w-0 truncate">{teacher.full_name} · {teacher.email}</span>
                    </label>
                  ))}
                  {teachers.length === 0 && <p className="p-2 text-xs text-danger">Create or activate a teacher account before assigning this course.</p>}
                </div>
              </fieldset>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-semibold text-green-900">
                  Course code
                  <input
                    required
                    minLength={2}
                    maxLength={50}
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    className="mt-1 h-10 w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink"
                  />
                </label>
                <label className="block text-sm font-semibold text-green-900">
                  Course name
                  <input
                    required
                    minLength={2}
                    maxLength={200}
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    className="mt-1 h-10 w-full rounded-lg border border-cream-300 px-3 text-sm font-normal text-ink"
                  />
                </label>
              </div>
              <label className="block text-sm font-semibold text-green-900">
                Description (optional)
                <textarea
                  rows={3}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-cream-300 p-3 text-sm font-normal text-ink"
                  placeholder="Describe this course"
                />
              </label>
              <label className="flex items-start gap-3 rounded-xl border border-cream-300 p-4 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={isPublished}
                  onChange={(event) => setIsPublished(event.target.checked)}
                  className="mt-0.5"
                />
                <span>
                  <span className="block font-semibold text-green-900">Publish course</span>
                  <span className="mt-1 block text-xs text-ink-muted">Published courses are available to enrolled students.</span>
                </span>
              </label>
              <fieldset className="rounded-xl border border-cream-300 p-3">
                <legend className="px-1 text-sm font-semibold text-green-900">
                  {editingCourse ? "Manage students" : "Add students"}
                </legend>
                {editingCourse && (
                  <>
                    <p className="mb-2 text-xs text-ink-muted">
                      {editingCourse.enrolled_students} students are currently enrolled. Removing a student keeps their course progress.
                    </p>
                    {studentIds.length > 0 && (
                      <div className="mb-3 space-y-1">
                        <p className="text-xs font-semibold text-green-900">Currently enrolled</p>
                        {studentIds.map((studentId) => {
                          const student = students.find((item) => item.id === studentId);
                          if (!student) return null;
                          return (
                            <div key={student.id} className="flex min-h-10 items-center justify-between gap-2 rounded-lg bg-green-50 px-2 text-sm text-ink">
                              <span className="min-w-0 truncate">{student.full_name} · {student.email}{!student.is_active && " · Inactive account"}</span>
                              <button
                                type="button"
                                onClick={() => setStudentIds((current) => current.filter((id) => id !== student.id))}
                                aria-label={`Remove ${student.full_name} from this course`}
                                className="shrink-0 rounded-md px-2 py-1 text-xs font-semibold text-danger hover:bg-red-50"
                              >
                                Remove
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
                <input
                  type="search"
                  value={studentSearch}
                  onChange={(event) => setStudentSearch(event.target.value)}
                  placeholder="Search students"
                  aria-label={editingCourse ? "Search students to manage" : "Search students to enroll"}
                  className="h-10 w-full rounded-lg border border-cream-300 px-3 text-sm"
                />
                <div className="mt-2 max-h-44 space-y-1 overflow-y-auto">
                  {students
                    .filter((student) => `${student.full_name} ${student.email}`.toLowerCase().includes(studentSearch.toLowerCase()))
                    .map((student) => (
                      <label key={student.id} className="flex min-h-10 items-center gap-2 rounded-lg px-2 text-sm text-ink hover:bg-cream-50">
                        <input
                          type="checkbox"
                          checked={studentIds.includes(student.id)}
                          disabled={!student.is_active && !studentIds.includes(student.id)}
                          onChange={() => setStudentIds((current) => current.includes(student.id)
                            ? current.filter((id) => id !== student.id)
                            : [...current, student.id])}
                        />
                        <span className="min-w-0 truncate">{student.full_name} · {student.email}{!student.is_active && " · Inactive account"}</span>
                      </label>
                    ))}
                  {students.length === 0 && <p className="p-2 text-xs text-ink-muted">No student accounts available.</p>}
                </div>
              </fieldset>
              <label className="flex items-start gap-3 rounded-xl border border-cream-300 p-4 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={enrollAll}
                  onChange={(event) => setEnrollAll(event.target.checked)}
                  className="mt-0.5"
                />
                <span>
                  <span className="block font-semibold text-green-900">Enroll all active students</span>
                  <span className="mt-1 block text-xs text-ink-muted">
                    {editingCourse
                      ? "Keep every active student enrolled. Clear this to manage the roster with the student selections above."
                      : "Selected by default. Clear this to enroll only the specifically selected students."}
                  </span>
                </span>
              </label>
              {loadError && <p role="alert" className="text-sm text-danger">{loadError}</p>}
              <div className="flex flex-col-reverse gap-2 border-t border-cream-200 pt-4 sm:flex-row sm:justify-end sm:gap-3">
                <Button type="button" variant="secondary" size="sm" className="w-full justify-center sm:w-auto" onClick={() => setIsOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm" className="w-full justify-center sm:w-auto" disabled={isSaving || teachers.length === 0 || teacherIds.length === 0}>
                  {isSaving ? <Loader2 size={15} className="animate-spin" /> : editingCourse ? <Pencil size={15} /> : <Plus size={15} />}
                  {editingCourse ? "Save changes" : "Create and enroll"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ), document.body)}
      {deletingCourse && createPortal((
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="Cancel course deletion"
            className="absolute inset-0 bg-green-900/50 backdrop-blur-sm"
            onClick={() => setDeletingCourse(null)}
          />
          <div role="alertdialog" aria-modal="true" aria-labelledby="delete-course-title" className="relative w-full max-w-md rounded-2xl border border-cream-300 bg-white p-5 shadow-2xl">
            <h2 id="delete-course-title" className="font-heading text-lg font-bold text-danger">Permanently delete course?</h2>
            <p className="mt-2 text-sm text-ink-muted">
              Deleting <strong>{deletingCourse.title}</strong> also removes its exams, attempts, results, tasks, enrollments, certificates, notices, and live classroom data. This cannot be undone.
            </p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button variant="secondary" size="sm" className="justify-center" onClick={() => setDeletingCourse(null)} disabled={isDeleting}>Cancel</Button>
              <Button variant="danger" size="sm" className="justify-center" onClick={() => void deleteCourse(deletingCourse)} disabled={isDeleting}>
                {isDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                Delete course and records
              </Button>
            </div>
          </div>
        </div>
      ), document.body)}
    </>
  );
}
