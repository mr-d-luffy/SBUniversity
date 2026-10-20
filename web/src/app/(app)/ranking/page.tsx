import { PageHeader } from "@/components/ui/Card";
import { RankBoard } from "@/components/features/RankBoard";

export const metadata = { title: "Live Ranking" };

export default async function RankingPage() {
  return (
    <>
      <PageHeader
        title="Top Performers"
        subtitle="Ranked by live Task Points from course assignments and examinations. Updates dynamically."
        action={
          <span className="flex items-center gap-2 text-sm text-ink-muted">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-success" />
            Live Database Sync
          </span>
        }
      />
      <RankBoard />
    </>
  );
}
