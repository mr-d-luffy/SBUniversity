"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "@clerk/nextjs";
import Image from "next/image";
import Link from "next/link";
import { CheckCircle2, KeyRound, Loader2, LockKeyhole } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { api, getDevAuthToken } from "@/lib/api";

type Course = {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  price: number;
  discount_percent: number;
  enrolled: boolean;
  unlocked: boolean;
  key_request_status?: "pending" | "approved" | "rejected" | "activated" | null;
};

function discountedPrice(course: Course) {
  return Number(course.price) * (1 - course.discount_percent / 100);
}

export default function StudentCoursesPage() {
  const { getToken } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [paymentCourseId, setPaymentCourseId] = useState("");
  const [key, setKey] = useState("");
  const [loading, setLoading] = useState(true);

  const resolveToken = useCallback(async () => {
    return await getToken() || (
      process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development"
        ? getDevAuthToken("student")
        : undefined
    );
  }, [getToken]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      if (!token) {
        setCourses([]);
        return;
      }
      setCourses(await api<Course[]>("/student/course-catalog", token));
      setError("");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load courses.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void load();
  }, [load]);

  async function requestKey(course: Course) {
    setBusy(course.id);
    setError("");
    try {
      const token = await resolveToken();
      await api(`/student/courses/${course.id}/key-requests`, token, { method: "POST" });
      setPaymentCourseId("");
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not request a course key.");
    } finally {
      setBusy("");
    }
  }

  async function activateKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("activate");
    setError("");
    try {
      const token = await resolveToken();
      await api("/student/course-key-activations", token, {
        method: "POST",
        body: JSON.stringify({ key: key.trim().toUpperCase() }),
      });
      setKey("");
      await load();
    } catch (activationError) {
      setError(activationError instanceof Error ? activationError.message : "Could not activate this key.");
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">Course catalog</h1>
        <p className="text-muted-foreground">Request a course key, then activate it once to keep lifetime access.</p>
      </header>

      <Card className="space-y-4 p-5">
        <div className="flex items-start gap-3">
          <KeyRound className="mt-1 shrink-0 text-green-700" />
          <div>
            <h2 className="font-semibold">Activate a course key</h2>
            <p className="text-sm text-muted-foreground">Keys use the format SB-XXXXX-XXXXX and can only be activated by the student they were issued to.</p>
          </div>
        </div>
        <form className="flex flex-col gap-3 sm:flex-row" onSubmit={activateKey}>
          <label className="sr-only" htmlFor="course-key">Course key</label>
          <input
            id="course-key"
            required
            minLength={14}
            maxLength={14}
            pattern="SB-[A-Z2-9]{5}-[A-Z2-9]{5}"
            value={key}
            onChange={(event) => setKey(event.target.value.toUpperCase())}
            placeholder="SB-XXXXX-XXXXX"
            className="h-11 min-w-0 flex-1 rounded-lg border border-cream-300 px-3 font-mono uppercase tracking-wide"
          />
          <Button type="submit" disabled={busy === "activate" || !key}>
            {busy === "activate" ? <Loader2 className="animate-spin" size={16} /> : <KeyRound size={16} />}
            Activate key
          </Button>
        </form>
        <p className="text-xs text-muted-foreground">After activation, this course remains unlocked for your account for life.</p>
      </Card>

      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 className="animate-spin text-green-700" />
        </div>
      ) : courses.length === 0 ? (
        <p>No published courses are available yet.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {courses.map((course) => {
            const showPayment = paymentCourseId === course.id;
            return (
              <Card key={course.id} className="space-y-3 p-5">
                <div className="flex items-center gap-2">
                  {course.unlocked ? <CheckCircle2 className="text-green-700" size={20} /> : <LockKeyhole className="text-ink-muted" size={20} />}
                  <span className="text-sm font-medium">{course.code}</span>
                  {course.unlocked && <span className="ml-auto text-xs font-semibold text-green-700">Unlocked for life</span>}
                </div>
                <h2 className="text-lg font-semibold">{course.title}</h2>
                <p className="text-sm text-muted-foreground">{course.description || "Explore course lessons and activities."}</p>
                <p className="text-sm">
                  {course.discount_percent > 0 && (
                    <span className="mr-2 text-muted-foreground line-through">{Number(course.price).toFixed(2)}</span>
                  )}
                  <span className="font-semibold">{discountedPrice(course).toFixed(2)}</span>
                  {course.discount_percent > 0 && <span className="ml-2 text-green-700">{course.discount_percent}% off</span>}
                </p>

                {course.unlocked ? (
                  <Link href={`/student/tasks?course_id=${encodeURIComponent(course.id)}`} className="inline-flex min-h-11 items-center rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white hover:bg-green-800">
                    Open course tasks
                  </Link>
                ) : course.key_request_status === "pending" ? (
                  <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Your key request is awaiting admin approval.</p>
                ) : course.key_request_status === "approved" ? (
                  <p className="rounded-lg bg-green-50 p-3 text-sm text-green-900">Approved. Enter the key shared by the admin above to unlock this course.</p>
                ) : showPayment ? (
                  <div className="space-y-3 rounded-xl border border-cream-300 bg-cream-50 p-4">
                    <p className="text-sm font-semibold">Scan to pay for this course</p>
                    <Image
                      src="/payment-qr.jpg"
                      alt="Course payment QR code"
                      width={260}
                      height={260}
                      className="mx-auto h-auto w-full max-w-[260px] rounded-lg"
                    />
                    <p className="text-xs text-muted-foreground">After payment, request your key. The admin will review it and provide a single-use activation key.</p>
                    <div className="flex flex-wrap gap-2">
                      <Button disabled={busy === course.id} onClick={() => void requestKey(course)}>
                        {busy === course.id ? <Loader2 className="animate-spin" size={16} /> : "Request key"}
                      </Button>
                      <Button variant="secondary" onClick={() => setPaymentCourseId("")}>Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <Button variant="primary" onClick={() => setPaymentCourseId(course.id)}>
                    Get key
                  </Button>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </main>
  );
}
