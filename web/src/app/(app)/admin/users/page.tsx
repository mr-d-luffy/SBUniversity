import { PageHeader } from "@/components/ui/Card";
import { UsersTable } from "@/components/features/UsersTable";

export const metadata = { title: "User Control | Admin" };

export default function AdminUsers() {
  return (
    <>
      <PageHeader
        title="User Control"
        subtitle="Manage roles and account status. Every action is audited and logged."
      />

      {/* Live, API-connected stats and users table */}
      <UsersTable />
    </>
  );
}
