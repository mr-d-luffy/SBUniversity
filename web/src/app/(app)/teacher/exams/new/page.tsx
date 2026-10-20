"use client";
import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, Trash2, CheckCircle2, Loader2, Upload } from "lucide-react";
import { PageHeader, Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface OptionDraft {
  text: string;
  isCorrect: boolean;
}

interface QuestionDraft {
  text: string;
  marks: number;
  options: OptionDraft[];
  explanation: string;
}

interface TeacherCourse {
  id: string;
  title: string;
  code: string;
}

interface TeacherDashboardResponse {
  my_courses: TeacherCourse[];
}

function toLocalDateTimeInput(date: Date): string {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  const source = text.replace(/^\uFEFF/, "");
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    if (char === '"' && quoted && source[index + 1] === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && source[index + 1] === "\n") index += 1;
      row.push(cell.trim());
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (quoted) throw new Error("The CSV has an unclosed quoted field.");
  row.push(cell.trim());
  if (row.some((value) => value.length > 0)) rows.push(row);
  return rows;
}

function questionsFromCsv(text: string): QuestionDraft[] {
  const rows = parseCsv(text);
  if (rows.length < 2) throw new Error("Add a header row and at least one question row.");
  const headers = rows[0].map((header) => header.trim().toLowerCase().replace(/\s+/g, "_"));
  const column = (name: string) => headers.indexOf(name);
  const questionColumn = column("question");
  const correctColumn = column("correct_answer");
  const optionColumns = ["option_a", "option_b", "option_c", "option_d"].map(column);
  if (questionColumn < 0 || correctColumn < 0 || optionColumns.slice(0, 2).some((index) => index < 0)) {
    throw new Error("CSV headers must include question, option_a, option_b, correct_answer; option_c, option_d, marks and explanation are optional.");
  }

  return rows.slice(1).map((values, rowIndex) => {
    const field = (index: number) => index < 0 ? "" : (values[index] ?? "").trim();
    const question = field(questionColumn);
    const options = optionColumns.map((index) => field(index)).filter(Boolean);
    const answer = field(correctColumn);
    if (!question || options.length < 2 || !answer) {
      throw new Error(`Row ${rowIndex + 2} needs a question, at least two options, and a correct_answer.`);
    }
    const answerIndex = /^[1-4]$/.test(answer)
      ? Number(answer) - 1
      : /^[a-d]$/i.test(answer)
        ? answer.toUpperCase().charCodeAt(0) - 65
        : options.findIndex((option) => option.toLowerCase() === answer.toLowerCase());
    if (answerIndex < 0 || answerIndex >= options.length) {
      throw new Error(`Row ${rowIndex + 2} correct_answer must be A–D, 1–4, or match an option exactly.`);
    }
    const marks = field(column("marks")) || "5";
    if (!Number.isFinite(Number(marks)) || Number(marks) <= 0) {
      throw new Error(`Row ${rowIndex + 2} marks must be a positive number.`);
    }
    return {
      text: question,
      marks: Number(marks),
      explanation: field(column("explanation")),
      options: options.map((option, index) => ({ text: option, isCorrect: index === answerIndex })),
    };
  });
}

export default function NewExamPage() {
  const router = useRouter();
  const toast = useToast();
  const { getToken } = useAuth();

  const [courses, setCourses] = useState<TeacherCourse[]>([]);
  const [courseId, setCourseId] = useState("");
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [startAt, setStartAt] = useState(() =>
    toLocalDateTimeInput(new Date(Date.now() + 60 * 60 * 1000))
  );
  const [endAt, setEndAt] = useState(() =>
    toLocalDateTimeInput(new Date(Date.now() + 24 * 60 * 60 * 1000))
  );
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("Attempt all questions. Server timer runs continuously.");
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [passMarks, setPassMarks] = useState(5);
  const [taskPoints, setTaskPoints] = useState(50);
  const [negativeMarking, setNegativeMarking] = useState(0);

  const [questions, setQuestions] = useState<QuestionDraft[]>([
    {
      text: "",
      marks: 5,
      explanation: "",
      options: [
        { text: "", isCorrect: true },
        { text: "", isCorrect: false },
        { text: "", isCorrect: false },
        { text: "", isCorrect: false },
      ],
    },
  ]);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadCourses = useCallback(async () => {
    setLoadingCourses(true);
    setCoursesError(null);
    try {
      const token = await resolveToken();
      const dashboard = await api<TeacherDashboardResponse>("/teacher/dashboard", token ?? undefined);
      setCourses(dashboard.my_courses);
      setCourseId((current) => current || dashboard.my_courses[0]?.id || "");
    } catch (err) {
      setCoursesError(err instanceof Error ? err.message : "Failed to load your courses.");
    } finally {
      setLoadingCourses(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  const addQuestion = () => {
    setQuestions((prev) => [
      ...prev,
      {
        text: "",
        marks: 5,
        explanation: "",
        options: [
          { text: "", isCorrect: true },
          { text: "", isCorrect: false },
          { text: "", isCorrect: false },
          { text: "", isCorrect: false },
        ],
      },
    ]);
  };

  const importQuestions = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const imported = questionsFromCsv(await file.text());
      setQuestions((current) => {
        const hasOnlyBlankStarter = current.length === 1 && !current[0].text.trim() && current[0].options.every((option) => !option.text.trim());
        return hasOnlyBlankStarter ? imported : [...current, ...imported];
      });
      toast(`Imported ${imported.length} question${imported.length === 1 ? "" : "s"}.`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not import this CSV file.");
    } finally {
      event.target.value = "";
    }
  };

  const removeQuestion = (index: number) => {
    setQuestions((prev) => prev.filter((_, i) => i !== index));
  };

  const updateQuestionText = (index: number, text: string) => {
    setQuestions((prev) =>
      prev.map((q, i) => (i === index ? { ...q, text } : q))
    );
  };

  const updateOptionText = (qIndex: number, optIndex: number, text: string) => {
    setQuestions((prev) =>
      prev.map((q, i) =>
        i === qIndex
          ? {
              ...q,
              options: q.options.map((opt, oi) => (oi === optIndex ? { ...opt, text } : opt)),
            }
          : q
      )
    );
  };

  const setCorrectOption = (qIndex: number, optIndex: number) => {
    setQuestions((prev) =>
      prev.map((q, i) =>
        i === qIndex
          ? {
              ...q,
              options: q.options.map((opt, oi) => ({
                ...opt,
                isCorrect: oi === optIndex,
              })),
            }
          : q
      )
    );
  };

  const handleSubmit = async (publishImmediately: boolean) => {
    if (!title.trim()) {
      toast("Please enter an exam title.");
      return;
    }
    if (!courseId) {
      toast("Select one of your courses.");
      return;
    }
    if (questions.some((question) =>
      !question.text.trim() ||
      question.marks <= 0 ||
      question.options.filter((option) => option.isCorrect).length !== 1 ||
      question.options.some((option) => !option.text.trim())
    )) {
      toast("Complete each question and its options, and select exactly one correct answer.");
      return;
    }
    if (passMarks > totalCalculatedMarks) {
      toast("Pass marks cannot be greater than the total marks.");
      return;
    }

    const start = new Date(startAt);
    const end = new Date(endAt);
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || end <= start) {
      toast("Choose a valid exam window. The end must be after the start.");
      return;
    }

    setIsSaving(true);
    let createdExamId: string | null = null;
    try {
      const token = await resolveToken();
      const createdExam = await api<{ id: string }>(
        "/exams",
        token ?? undefined,
        {
          method: "POST",
          body: JSON.stringify({
            course_id: courseId,
            title: title.trim(),
            instructions: instructions.trim() || null,
            duration_minutes: durationMinutes,
            pass_marks: passMarks,
            negative_marking: negativeMarking,
            start_at: start.toISOString(),
            end_at: end.toISOString(),
          }),
        }
      );
      createdExamId = createdExam.id;

      for (const [index, question] of questions.entries()) {
        await api(
          `/exams/${createdExam.id}/questions`,
          token ?? undefined,
          {
            method: "POST",
            body: JSON.stringify({
              text: question.text.trim(),
              marks: question.marks,
              position: index + 1,
              explanation: question.explanation.trim() || null,
              options: question.options.map((option, optionIndex) => ({
                text: option.text.trim(),
                is_correct: option.isCorrect,
                position: optionIndex + 1,
              })),
            }),
          }
        );
      }

      if (publishImmediately) {
        await api(
          `/exams/${createdExam.id}/publish`,
          token ?? undefined,
          {
            method: "POST",
            body: JSON.stringify({ task_points: taskPoints }),
          }
        );
      }

      toast(publishImmediately ? `Published "${title}".` : `Saved "${title}" as a draft.`);
      router.push("/teacher/exams");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save the exam.";
      toast(createdExamId ? `Exam draft ${createdExamId} was created, but setup failed: ${message}` : message);
    } finally {
      setIsSaving(false);
    }
  };

  const totalCalculatedMarks = questions.reduce((sum, q) => sum + (Number(q.marks) || 0), 0);

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex items-center gap-2">
        <Button href="/teacher/exams" variant="secondary" size="sm" className="min-h-11">
          <ArrowLeft size={14} /> Back to Exams
        </Button>
      </div>

      <PageHeader
        title="Create New Examination"
        subtitle="Configure exam details, duration, question bank, and linked Task Points."
      />

      {coursesError ? (
        <Card className="p-5 text-sm text-danger">
          <p>{coursesError}</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={() => void loadCourses()}>
            Retry Loading Courses
          </Button>
        </Card>
      ) : !loadingCourses && courses.length === 0 ? (
        <Card className="p-5 text-sm text-ink-muted">
          No courses are assigned to your account yet. You need an assigned course before creating an exam.
        </Card>
      ) : null}

      <div className="grid min-w-0 gap-6 lg:grid-cols-12 lg:gap-8 lg:items-start">
        {/* Left Form: Exam Configuration */}
        <div className="space-y-6 lg:col-span-8">
          <Card className="min-w-0 space-y-4 p-4 sm:p-6">
            <h3 className="font-heading text-lg font-bold text-green-900 border-b border-cream-200 pb-3">
              1. Basic Information & Parameters
            </h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Exam Title
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Advanced Graph Algorithms Midterm"
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Select Course
                </label>
                <select
                  value={courseId}
                  onChange={(e) => setCourseId(e.target.value)}
                  disabled={loadingCourses || courses.length === 0}
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                >
                  {loadingCourses ? (
                    <option value="">Loading courses...</option>
                  ) : courses.length === 0 ? (
                    <option value="">No courses assigned</option>
                  ) : courses.map((item) => (
                    <option key={item.id} value={item.id}>{item.code} – {item.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Duration (Minutes)
                </label>
                <input
                  type="number"
                  min="5"
                  max="180"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Pass Marks
                </label>
                <input
                  type="number"
                  min="0"
                  value={passMarks}
                  onChange={(e) => setPassMarks(Number(e.target.value))}
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Task Points Awarded on Passing
                </label>
                <input
                  type="number"
                  min="0"
                  value={taskPoints}
                  onChange={(e) => setTaskPoints(Number(e.target.value))}
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm font-bold text-bordo-700 focus:border-green-700 focus:outline-none"
                />
                <span className="text-[11px] text-ink-muted">Earned automatically when student passes</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Opens At
                </label>
                <input
                  type="datetime-local"
                  required
                  value={startAt}
                  onChange={(e) => setStartAt(e.target.value)}
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Closes At
                </label>
                <input
                  type="datetime-local"
                  required
                  value={endAt}
                  onChange={(e) => setEndAt(e.target.value)}
                  className="h-11 min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-green-900 mb-1">
                Candidate Instructions
              </label>
              <textarea
                rows={2}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                className="min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white p-3 text-sm text-ink focus:border-green-700 focus:outline-none"
              />
            </div>
          </Card>

          {/* Question Bank Builder */}
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-heading text-lg font-bold text-green-900">
                  2. Question Bank ({questions.length} Questions)
                </h3>
                <p className="text-xs text-ink-muted">Single choice MCQ with automated evaluation</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <label className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border border-cream-300 bg-white px-3 text-sm font-semibold text-green-900 transition-colors hover:bg-cream-100">
                  <Upload size={15} /> Import CSV
                  <input type="file" accept=".csv,text/csv" onChange={(event) => void importQuestions(event)} className="sr-only" aria-label="Import questions from CSV" />
                </label>
                <Button type="button" variant="secondary" size="sm" className="min-h-11" onClick={addQuestion}>
                  <Plus size={15} /> Add Question
                </Button>
              </div>
            </div>
            <p className="text-xs text-ink-muted">
              CSV columns: <code>question, option_a, option_b, option_c, option_d, correct_answer, marks, explanation</code>. Correct answer can be A–D, 1–4, or the exact option text. <a className="font-semibold text-green-800 underline" download="sb-university-question-template.csv" href={`data:text/csv;charset=utf-8,${encodeURIComponent('question,option_a,option_b,option_c,option_d,correct_answer,marks,explanation\n"What is 2 + 2?","3","4","5","6",B,5,"Basic addition"')}`}>Download template</a>.
            </p>

            {questions.map((q, qIndex) => (
              <Card key={qIndex} className="min-w-0 space-y-4 border-l-4 border-l-green-700 p-4 sm:p-5">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cream-200 pb-2">
                  <span className="font-heading text-sm font-bold text-green-900">
                    Question #{qIndex + 1}
                  </span>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1.5 text-xs text-ink-muted">
                      Marks
                      <input
                        type="number"
                        min="0.1"
                        step="0.1"
                        value={q.marks}
                        onChange={(e) => setQuestions((prev) =>
                          prev.map((item, i) => i === qIndex ? { ...item, marks: Number(e.target.value) } : item)
                        )}
                        className="h-10 w-16 rounded border border-cream-300 px-2 text-ink"
                      />
                    </label>
                    {questions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeQuestion(qIndex)}
                        className="grid h-11 w-11 place-items-center rounded-lg text-danger hover:bg-danger-bg hover:text-danger/80"
                        title="Remove Question"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-ink-muted mb-1">
                    Question Prompt
                  </label>
                  <textarea
                    rows={2}
                    value={q.text}
                    onChange={(e) => updateQuestionText(qIndex, e.target.value)}
                    placeholder="Enter the question text here..."
                    className="w-full rounded-lg border border-cream-300 bg-white p-2.5 text-sm text-ink focus:border-green-700 focus:outline-none"
                  />
                </div>

                {/* Options */}
                <div className="space-y-2">
                  <label className="block text-xs font-semibold text-green-900">
                    Options (Select radio for single correct answer):
                  </label>
                  {q.options.map((opt, optIndex) => (
                    <div key={optIndex} className="flex min-w-0 items-center gap-2">
                      <label className="grid h-11 w-11 shrink-0 cursor-pointer place-items-center">
                        <input
                          type="radio"
                          name={`correct-${qIndex}`}
                          checked={opt.isCorrect}
                          onChange={() => setCorrectOption(qIndex, optIndex)}
                          className="h-5 w-5 text-green-700 focus:ring-green-700"
                          aria-label={`Mark option ${optIndex + 1} as correct`}
                        />
                      </label>
                      <input
                        type="text"
                        value={opt.text}
                        onChange={(e) => updateOptionText(qIndex, optIndex, e.target.value)}
                        placeholder={`Option ${optIndex + 1}`}
                        className={`h-10 min-w-0 flex-1 rounded-lg border px-2 text-xs focus:outline-none sm:px-3 ${
                          opt.isCorrect
                            ? "border-green-700 bg-green-50 font-semibold text-green-900"
                            : "border-cream-300 bg-white text-ink"
                        }`}
                      />
                      {opt.isCorrect && (
                        <span className="flex shrink-0 items-center gap-1 whitespace-nowrap text-[10px] font-bold text-success sm:text-[11px]">
                          <CheckCircle2 size={13} /> Correct
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                <div>
                  <label className="block text-xs font-medium text-ink-muted mb-1">
                    Explanation (optional)
                  </label>
                  <textarea
                    rows={2}
                    value={q.explanation}
                    onChange={(e) => setQuestions((prev) =>
                      prev.map((item, i) => i === qIndex ? { ...item, explanation: e.target.value } : item)
                    )}
                    className="min-w-0 max-w-full w-full rounded-lg border border-cream-300 bg-white p-2.5 text-sm text-ink focus:border-green-700 focus:outline-none"
                  />
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Right Sticky Sidebar: Summary & Publish Actions */}
        <div className="min-w-0 space-y-6 lg:col-span-4">
          <Card className="space-y-4 p-4 sm:p-5 lg:sticky lg:top-24">
            <h4 className="font-heading text-base font-bold text-green-900 border-b border-cream-200 pb-2">
              Exam Summary
            </h4>

            <div className="space-y-2 text-xs text-ink-muted">
              <div className="flex justify-between gap-3">
                <span>Total Questions:</span>
                <span className="font-bold text-ink">{questions.length}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span>Total Marks:</span>
                <span className="font-bold text-ink">{totalCalculatedMarks}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span>Pass Marks:</span>
                <span className="font-bold text-ink">{passMarks}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span>Duration:</span>
                <span className="font-bold text-ink">{durationMinutes} mins</span>
              </div>
              <div className="flex justify-between gap-3 border-t border-cream-200 pt-2">
                <span>Linked Task Points:</span>
                <span className="font-bold text-bordo-700">+{taskPoints} pts</span>
              </div>
            </div>

            <div className="border-t border-cream-200 pt-3 space-y-2">
              <Button
                type="button"
                variant="primary"
                size="md"
                className="min-h-11 w-full"
                disabled={isSaving || loadingCourses || courses.length === 0}
                onClick={() => void handleSubmit(true)}
              >
                {isSaving ? <Loader2 size={16} className="animate-spin" /> : "Publish Exam Now"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="md"
                className="min-h-11 w-full"
                disabled={isSaving || loadingCourses || courses.length === 0}
                onClick={() => void handleSubmit(false)}
              >
                {isSaving ? <Loader2 size={16} className="animate-spin" /> : "Save as Draft"}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
