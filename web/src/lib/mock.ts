// Demo data. Replace each export with an `api()` call once the FastAPI backend is live.
export interface RankedStudent { id: string; name: string; points: number; tasks: number }
export interface Task { id: number; title: string; course: string; points: number; type: "exam" | "assignment"; due: string; status: "open" | "pending" | "done" }
export interface Submission { id: number; student: string; task: string; note: string; points: number }
export interface Notice { id: number; title: string; body: string; author: string; priority: "normal" | "important" | "urgent"; pinned?: boolean }

export const ME_ID = "s1";

export const leaderboard: RankedStudent[] = [
  { id: "s2", name: "Isha Patil", points: 520, tasks: 15 },
  { id: "s3", name: "Kabir Nair", points: 455, tasks: 13 },
  { id: "s4", name: "khushi Joshi", points: 410, tasks: 12 },
  { id: "s5", name: "Vikram Rao", points: 300, tasks: 8 },
  { id: "s1", name: "Aarav Sharma", points: 290, tasks: 9 },
  { id: "s6", name: "Neha Kulkarni", points: 260, tasks: 7 },
];

export const tasks: Task[] = [
  { id: 1, title: "Pass the Data Structures midterm", course: "Data Structures", points: 50, type: "exam", due: "Oct 20", status: "open" },
  { id: 2, title: "Binary tree write-up", course: "Data Structures", points: 30, type: "assignment", due: "Oct 24", status: "open" },
  { id: 3, title: "Complexity analysis quiz", course: "Algorithms", points: 40, type: "assignment", due: "Oct 18", status: "pending" },
  { id: 4, title: "Lab report 3", course: "Python Basics", points: 60, type: "assignment", due: "Oct 05", status: "done" },
];

export const courses = [
  { name: "Python Basics", progress: 100 },
  { name: "Data Structures", progress: 50 },
  { name: "Algorithms", progress: 25 },
];

export const exams = [
  { id: 1, title: "Data Structures midterm", course: "Data Structures", questions: 20, minutes: 45, window: "Oct 18 – Oct 20", points: 50 },
  { id: 2, title: "Algorithms unit test 1", course: "Algorithms", questions: 15, minutes: 30, window: "Oct 26 – Oct 27", points: 40 },
];

export const submissions: Submission[] = [
  { id: 1, student: "Aarav Sharma", task: "Complexity analysis quiz", note: "drive.link/aarav-quiz", points: 40 },
  { id: 2, student: "Kabir Nair", task: "Binary tree write-up", note: "Notes on in-order and level-order traversal.", points: 30 },
  { id: 3, student: "Vikram Rao", task: "Binary tree write-up", note: "drive.link/vikram-trees", points: 30 },
];

export const notices: Notice[] = [
  { id: 1, title: "Midterm schedule published", body: "The Data Structures midterm opens Oct 18 and closes Oct 20 at 6 PM. You have one attempt of 45 minutes.", author: "Dr. Meera Iyer", priority: "important", pinned: true },
  { id: 2, title: "Portal maintenance tonight", body: "Results and certificates will be unavailable from 1 AM to 2 AM.", author: "Admin", priority: "urgent" },
  { id: 3, title: "Library closes early on Friday", body: "The central library closes at 4 PM this Friday for maintenance.", author: "Admin", priority: "normal" },
];

export const adminUsers = [
  ...leaderboard.map((s) => ({ id: s.id, name: s.name, role: "student" as const, points: s.points, active: true })),
  { id: "t1", name: "Dr. Meera Iyer", role: "teacher" as const, points: 0, active: true },
];
