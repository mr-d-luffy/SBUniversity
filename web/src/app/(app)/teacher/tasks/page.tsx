import { PageHeader } from "@/components/ui/Card";
import { ApprovalQueue } from "@/components/features/ApprovalQueue";
import { TeacherTaskCreator } from "@/components/features/TeacherTaskCreator";

export const metadata = { title: "Task Approvals | Faculty" };

export default function TeacherTasks() {
  return (
    <>
      <PageHeader
        title="Tasks & Student Approvals"
        subtitle="Create video or learning tasks for any course and student. Linked tasks award points automatically when completed; legacy submissions remain in the review queue."
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
      <ApprovalQueue />
    </>
  );
}
