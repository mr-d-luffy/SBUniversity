import { AdminCourseKeyRequests } from "@/components/features/AdminCourseKeyRequests";
import { PageHeader } from "@/components/ui/Card";

export const metadata = { title: "Course Key Approvals | Admin" };

export default function AdminCourseKeysPage() {
  return (
    <>
      <PageHeader
        title="Course Key Approvals"
        subtitle="Review student requests, issue activation keys, and copy approved keys."
      />
      <AdminCourseKeyRequests />
    </>
  );
}
