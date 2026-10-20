import { PageHeader } from "@/components/ui/Card";
import { TaskList } from "@/components/features/TaskList";

export const metadata = { title: "My Tasks" };

export default function TasksPage() {
  return (
    <>
      <PageHeader
        title="My Tasks & Assignments"
        subtitle="Finish course tasks and lab assessments to earn Task Points. Points are credited automatically."
        action={
          <span className="flex items-center gap-2 text-sm text-ink-muted">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-success" />
            Live Sync
          </span>
        }
      />
      <TaskList />
    </>
  );
}
