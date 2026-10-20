import { PageHeader } from "@/components/ui/Card";
import { AdminCourses } from "@/components/features/AdminCourses";

export const metadata = { title: "Course Control | Admin" };

export default function AdminCoursesPage() {
  return (
    <>
      <PageHeader
        title="Course Control"
        subtitle="Create and publish courses, with active-student enrollment enabled by default."
      />
      <AdminCourses />
    </>
  );
}
