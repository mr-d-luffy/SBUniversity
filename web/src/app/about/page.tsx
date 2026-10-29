import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { readFileSync } from "node:fs";
import path from "node:path";
import { GraduationCap, ShieldCheck, ScrollText, Scale } from "lucide-react";
import { AboutBackButton } from "@/components/features/AboutBackButton";

export const metadata: Metadata = {
  title: "About, Privacy Policy, Terms of Use & License",
  description: "Learn about SiliconBrains University and read our Privacy Policy, Terms of Use and software license.",
  alternates: { canonical: "/about" },
};

const licenseText = readFileSync(path.resolve(process.cwd(), "../LICENSE.md"), "utf8");

const privacySections = [
  { title: "1. Data we handle", paragraphs: ["SiliconBrains University processes account details (name, email and profile image), student or teacher profile information (such as phone, academic affiliation, student or employee code, and optional date of birth), and records created while using the platform."], bullets: ["Learning records can include course enrolments, tasks and submissions, exam answers and results, certificates, activity summaries, planner entries, assistant conversations, community messages and whiteboard content.", "The service also processes authentication/session data and technical security events needed to protect accounts and operate the platform."] },
  { title: "2. Why we use it", paragraphs: ["We use this information to authenticate users; provide course, assessment, credential and communication features; administer academic records; support users; maintain platform security; and meet applicable legal obligations. Profile details can be corrected in the profile tools where available. We do not use learning activity for targeted advertising."] },
  { title: "3. Service providers and transfers", paragraphs: ["The platform uses Clerk for authentication, configured database and hosting providers for application data, and Supabase Storage when configured for uploaded files. The learning assistant may send the prompt and conversation context you submit to the configured AI provider to generate a response. Provider locations and retention depend on the deployment configuration; contact us for current processor details. Providers may process data outside India, subject to applicable requirements."] },
  { title: "4. Retention and deletion", paragraphs: ["Account and learning data are retained while needed to operate the service and maintain academic records. You can request account deletion from your profile. Deletion removes the account and associated records from the application where dependencies permit; some records may need to be retained where law requires it. Backups and third-party systems may take time to expire, and this project does not yet publish a verified backup expiry schedule."] },
  { title: "5. Children", paragraphs: ["The platform is designed for educational use and may be used by students under 18. The current signup flow does not implement an age gate or verifiable parental-consent workflow. Institutions and guardians should contact us before enrolling a child; this notice does not claim that a parental-verification process is currently available."] },
  { title: "6. Your choices and rights", paragraphs: ["You can view your account profile and update supported fields in the portal. You can request a copy, correction, deletion, or other assistance by emailing privacy@siliconbrains.in. Identity verification may be needed before we disclose or delete information. If you are not satisfied with our response, you may use the grievance and complaint routes available under applicable law, including the Data Protection Board of India where applicable."] },
  { title: "7. Security", paragraphs: ["The service uses authenticated access, role-based authorization, transport security, and security event logging. No online service can guarantee absolute security. If you suspect unauthorized access to your account or data, contact privacy@siliconbrains.in promptly."] },
  { title: "8. Contact and review", paragraphs: ["For privacy requests or grievances, contact privacy@siliconbrains.in. Notice version 2.0, reviewed 28 October 2026. This notice describes current application behaviour and should be reviewed by the organization’s privacy/legal owner before production use."] },
];

const termsSections = [
  { title: "1. About the Service", text: "SiliconBrains University provides online learning and academic administration features, which may include courses, lessons, exams, assignments, progress tracking, rankings, notices, credentials and learning assistance. Features may change as the service develops." },
  { title: "2. Accounts and Eligibility", text: "You must provide accurate account information, keep your sign-in credentials private and use only accounts assigned or authorized for you. If you are under 18, use the service with the permission and involvement of a parent, guardian or educational institution." },
  { title: "3. Acceptable Use", text: "Use the service lawfully and respectfully. Do not access another person's account or data without permission, disrupt or probe the service, upload malicious code, misrepresent your identity, or use the platform to harass, threaten or harm others." },
  { title: "4. Courses, Exams and Academic Work", text: "Follow the instructions and academic integrity rules set by your institution and instructors. Do not cheat, impersonate another learner, share restricted exam content, or interfere with assessments. Instructors and institutions are responsible for their course requirements, grading decisions and academic policies." },
  { title: "5. Your Content", text: "You retain responsibility for content you submit, including messages, answers, files and assignment work. You confirm that you have the right to submit it. You grant SiliconBrains University permission to store, process and display that content only as needed to operate the service and provide its features to you and your institution." },
  { title: "6. Credentials and Results", text: "Results, rankings, completion records and certificates are provided for educational use and may depend on information submitted by users or institutions. Verification tools confirm the records available to the platform at the time of a check; they do not replace an institution's official decision or records." },
  { title: "7. AI and Automated Features", text: "Learning assistant responses are generated to support study and may be incomplete or inaccurate. They are not professional, institutional or grading advice. Review important information with your instructor and do not submit sensitive personal information unless the feature specifically requires it." },
  { title: "8. Intellectual Property", text: "The platform's software, branding, design and materials are owned by SiliconBrains or its licensors. You may use them only through the service and for its intended educational purposes. Do not copy, modify, distribute or commercially exploit them without permission, except where applicable law allows." },
  { title: "9. Availability and Third-Party Services", text: "We work to keep the service available and secure, but access may be interrupted for maintenance, updates or events outside our control. The service may rely on third-party providers or link to their services; their own terms and privacy policies apply." },
  { title: "10. Suspension and Termination", text: "Access may be restricted or suspended if an account violates these terms, creates a security risk or must be restricted by law or an institution. Where practical, we will provide notice and an opportunity to address the issue. You may stop using the service at any time; institutional records may remain subject to the institution's retention requirements." },
  { title: "11. Updates to These Terms", text: "We may update these terms as the service changes. The revised version will be posted on this page with an updated effective date. Continued use after that date means you accept the revised terms; if you do not agree, stop using the service." },
  { title: "12. Contact", text: "For questions about these terms, contact privacy@siliconbrains.in." },
];

const teamMembers = [
  { name: "Mohit Shivankar", role: "Team Leader", image: "/team/mohit-shivankar-portrait.jpeg", featured: true },
  { name: "Vaishnavi Mohite", role: "Chief Technology Officer", image: "/team/vaishnavi-mohite-portrait.jpeg" },
  { name: "Mohit Gurnule", role: "Chief Security Manager", image: "/team/mohit-gurnule-portrait.jpeg" },
  { name: "Hemant Tripathi", role: "Project Manager", image: "/team/hemant-tripathi-portrait.jpeg" },
  { name: "Raj Pande", role: "Social Media Manager", image: "/team/raj-pande-portrait.jpeg" },
  { name: "Shlok Thakur", role: "Team Manager", image: "/team/shlok-thakur-portrait.jpg" },
];

function PolicySection({ section }: { section: { title: string; paragraphs?: string[]; bullets?: string[]; after?: string } }) {
  return (
    <section className="border-t border-cream-200 py-5 first:border-0 first:pt-0">
      <h3 className="font-heading text-base font-bold text-green-900">{section.title}</h3>
      {section.paragraphs?.map((text) => <p key={text} className="mt-2 text-sm leading-7 text-ink-muted">{text}</p>)}
      {section.bullets && <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-7 text-ink-muted">{section.bullets.map((text) => <li key={text}>{text}</li>)}</ul>}
      {section.after && <p className="mt-2 text-sm leading-7 text-ink-muted">{section.after}</p>}
    </section>
  );
}

export default function AboutPage() {
  return (
    <div className="about-page-enter min-h-dvh bg-cream-50 text-ink">
      <header className="border-b border-cream-300 bg-white px-4 py-4 sm:px-8">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <Link href="/" className="flex min-w-0 items-center gap-2.5 font-heading text-base font-bold text-green-700 sm:text-lg">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-green-700 text-cream-200"><GraduationCap size={20} /></span>
            <span className="truncate">SiliconBrains University</span>
          </Link>
          <AboutBackButton />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-16">
        <div className="text-center">
          <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700"><GraduationCap size={14} /> About SiliconBrains University</span>
          <h1 className="font-heading text-2xl font-bold text-green-900 sm:text-4xl">Learning, assessment and academic records in one place</h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-ink-muted">SiliconBrains University brings students, teachers and administrators together with tools for courses, exams, assignments, progress and verifiable academic credentials.</p>
        </div>

        <section id="team" className="mt-10 scroll-mt-24 sm:mt-14">
          <div className="mx-auto max-w-2xl text-center">
            <span className="inline-flex items-center rounded-full border border-green-700/15 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-green-700">The people behind the platform</span>
            <h2 className="mt-3 font-heading text-2xl font-bold text-green-900 sm:text-3xl">Meet the development team</h2>
            <p className="mt-2 text-sm leading-6 text-ink-muted">A cross-functional team bringing together product leadership, technology, finance, project delivery and community.</p>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {teamMembers.map((member, index) => (
              <article
                key={member.name}
                className={`team-member-enter group overflow-hidden rounded-2xl border shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg ${member.featured ? "border-green-700/40 bg-green-50" : "border-cream-300 bg-white"}`}
                style={{ animationDelay: `${index * 85}ms` }}
              >
                <div className="bg-gradient-to-b from-green-900 to-green-700 p-3 pb-0 sm:p-4 sm:pb-0">
                  <div className="relative mx-auto aspect-[4/5] w-full max-w-[250px] overflow-hidden rounded-t-xl bg-green-900 shadow-xl ring-1 ring-white/30">
                    <Image
                      src={member.image}
                      alt={`Portrait of ${member.name}`}
                      fill
                      priority={index === 0}
                      sizes="(max-width: 639px) 80vw, (max-width: 1023px) 40vw, 250px"
                      className="object-cover object-center"
                    />
                  </div>
                </div>
                <div className="flex min-h-[88px] items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <h3 className="break-words font-heading text-base font-bold text-green-900">{member.name}</h3>
                    <p className="mt-1 text-sm text-ink-muted">{member.role}</p>
                  </div>
                  {member.featured && <span className="shrink-0 rounded-full bg-green-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-green-800">Lead</span>}
                </div>
              </article>
            ))}
          </div>
        </section>

        <nav aria-label="On this page" className="sticky top-3 z-10 mx-auto mt-8 flex w-fit max-w-full flex-wrap justify-center gap-2 rounded-2xl border border-cream-300 bg-white/95 p-2 shadow-sm backdrop-blur">
          <a href="#team" className="inline-flex min-h-10 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-green-900 hover:bg-green-50"><GraduationCap size={16} /> Team</a>
          <a href="#privacy" className="inline-flex min-h-10 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-green-900 hover:bg-green-50"><ShieldCheck size={16} /> Privacy Policy</a>
          <a href="#terms" className="inline-flex min-h-10 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-green-900 hover:bg-green-50"><ScrollText size={16} /> Terms of Use</a>
          <a href="#license" className="inline-flex min-h-10 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-green-900 hover:bg-green-50"><Scale size={16} /> License</a>
        </nav>

        <section id="privacy" className="mt-8 scroll-mt-24 rounded-2xl border border-cream-300 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-cream-200 pb-5">
            <div><p className="text-xs font-bold uppercase tracking-wide text-green-700">Document reference SB-PP-0001</p><h2 className="mt-1 font-heading text-2xl font-bold text-green-900">Privacy Policy</h2></div>
            <p className="rounded-full bg-cream-100 px-3 py-1 text-xs font-semibold text-ink-muted">Effective 28 October 2026</p>
          </div>
          <p className="mt-5 text-sm leading-7 text-ink-muted">This notice describes personal data processed by SiliconBrains University when you use its learning platform, academic tools and related services. It is an engineering-facing description of the current application; the organization should have its privacy/legal owner verify the notice and operational practices.</p>
          <div className="mt-6">{privacySections.map((section) => <PolicySection key={section.title} section={section} />)}</div>
        </section>

        <section id="license" className="mt-8 scroll-mt-24 rounded-2xl border border-cream-300 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-cream-200 pb-5">
            <div><p className="text-xs font-bold uppercase tracking-wide text-green-700">SiliconBrains Software &amp; Technology Division</p><h2 className="mt-1 font-heading text-2xl font-bold text-green-900">Software License Agreement</h2></div>
            <p className="rounded-full bg-cream-100 px-3 py-1 text-xs font-semibold text-ink-muted">Version 1.0 · Effective 18 October 2026</p>
          </div>
          <pre className="mt-5 overflow-x-auto whitespace-pre-wrap break-words font-sans text-sm leading-7 text-ink-muted">{licenseText}</pre>
        </section>

        <section id="terms" className="mt-8 scroll-mt-24 rounded-2xl border border-cream-300 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-cream-200 pb-5">
            <div><p className="text-xs font-bold uppercase tracking-wide text-green-700">SiliconBrains University</p><h2 className="mt-1 font-heading text-2xl font-bold text-green-900">Terms of Use</h2></div>
            <p className="rounded-full bg-cream-100 px-3 py-1 text-xs font-semibold text-ink-muted">Effective 22 October 2026</p>
          </div>
          <p className="mt-5 text-sm leading-7 text-ink-muted">These Terms of Use explain the basic rules for accessing and using the SiliconBrains University website and learning platform. By using the service, you agree to follow these terms and any course or institution rules that apply to you.</p>
          <div className="mt-6 space-y-5">{termsSections.map((section) => <PolicySection key={section.title} section={{ title: section.title, paragraphs: [section.text] }} />)}</div>
        </section>

        <div className="mt-8 flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm text-green-700">
          <Link href="/" className="font-semibold hover:underline">Home</Link>
          <Link href="/verify" className="font-semibold hover:underline">Verify a credential</Link>
          <a href="mailto:privacy@siliconbrains.in" className="font-semibold hover:underline">Contact privacy officer</a>
        </div>
      </main>
    </div>
  );
}
