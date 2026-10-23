import { PageHeader } from "@/components/ui/Card";
import { ApprovalQueue } from "@/components/features/ApprovalQueue";
import { TeacherTaskCreator } from "@/components/features/TeacherTaskCreator";
import { TeacherTaskManager } from "@/components/features/TeacherTaskManager";

export const metadata = { title: "Task Approvals | Faculty" };

export default function TeacherTasks() {
  return (
    <>
      <PageHeader
        title="Tasks & Student Approvals"
        subtitle="Create and fully update course tasks. Linked tasks award points automatically when completed; submissions remain in the review queue."
        action={
          <div className="flex w-full flex-wrap items-center gap-3 sm:w-auto">
            <span className="flex min-h-11 items-center gap-2 text-sm text-ink-muted">
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-success" />
              Live Sync
            </span>
            <TeacherTaskCreator />
          </div>
        }
      />
      <section className="mt-6 space-y-3" aria-labelledby="task-approval-heading">
        <div className="flex items-center justify-between gap-3">
          <h2 id="task-approval-heading" className="font-heading text-xl font-bold text-green-900">Pending Task Approvals</h2>
        </div>
        <ApprovalQueue />
      </section>
      <TeacherTaskManager />
    </>
  );
}
