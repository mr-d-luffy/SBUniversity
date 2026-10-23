import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, GraduationCap, ShieldCheck, ScrollText } from "lucide-react";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "About, Privacy Policy & Terms of Use",
  description: "Learn about SiliconBrains University and read our Privacy Policy and Terms of Use.",
  alternates: { canonical: "/about" },
};

const privacySections = [
  { title: "1. Who We Are", paragraphs: ["SiliconBrains is an independent web engineering practice led by a Senior Web Engineer. For the purposes of applicable data protection law, we act as the Data Fiduciary / Data Controller of personal data collected through the Website."], bullets: ["Business name: SiliconBrains (Silicon Brains)", "Website: www.siliconbrains.in", "Privacy contact: privacy@siliconbrains.in", "Location: Nagpur, India, 440034"] },
  { title: "2. Information We Collect", paragraphs: ["We collect only the information needed to operate the Website and deliver our services."], bullets: ["Information you provide: name, email address, phone number, company name, project details, budget and timeline, and any files or messages you send through contact forms, email or chat.", "Client project data: credentials, repository access, content, analytics or user data that you share with us while we deliver a project. This is handled under Section 8.", "Technical data collected automatically: IP address, browser type and version, device type, operating system, referring page, pages viewed, time spent, and approximate location derived from IP.", "Cookies and similar technologies: see Section 5.", "Communications: records of emails, calls and meetings relating to enquiries and engagements.", "Payment and billing data: invoicing details only. Card or bank details are processed by third-party payment providers and are not stored on our servers."] },
  { title: "3. How We Use Your Information", bullets: ["To respond to enquiries, prepare proposals and quotations, and deliver contracted services.", "To operate, secure, debug and improve the Website and its performance.", "To send project updates, invoices, and service-related notices.", "To send newsletters or marketing messages only where you have opted in; you can withdraw at any time.", "To analyse aggregated usage and understand how visitors use the Website.", "To detect, prevent and respond to fraud, abuse, spam and security incidents.", "To comply with legal, tax and accounting obligations and to enforce our agreements."] },
  { title: "4. Legal Basis for Processing", paragraphs: ["Depending on your location, we process personal data on one or more of the following bases: your consent (including consent under the Digital Personal Data Protection Act, 2023 of India); performance of a contract or steps taken at your request before entering a contract; our legitimate interests in running and securing a professional services business; and compliance with legal obligations."] },
  { title: "5. Cookies and Tracking Technologies", paragraphs: ["Cookies are small text files stored on your device. We use the following categories:"], bullets: ["Strictly necessary: required for security, load balancing and core site functionality.", "Preferences: remember settings such as theme or language.", "Analytics: help us understand traffic and performance, using privacy-respecting configurations where possible.", "Marketing: used only with your consent."], after: "You can control or delete cookies through your browser settings or our cookie banner. Blocking some cookies may affect how the Website works." },
  { title: "6. Third-Party Services", paragraphs: ["We rely on trusted providers to run the Website and our services. These may include hosting and CDN providers, analytics tools, email and form-handling services, code hosting platforms, error monitoring, scheduling tools and payment processors. They process data only on our instructions or under their own privacy terms, and only as needed to provide their service. We do not sell your personal data. The Website may link to external sites; we are not responsible for their privacy practices."] },
  { title: "7. Sharing and Disclosure", paragraphs: ["We share personal data only: (a) with service providers described above; (b) with professional advisers such as accountants and lawyers under confidentiality; (c) where required by law, court order or government authority; (d) to protect our rights, safety or property; and (e) in connection with a business transfer, with notice to you where required."] },
  { title: "8. Client Project Data and Confidentiality", paragraphs: ["When we work on a client's website or application, we may access source code, databases, credentials and end-user data belonging to the client. In that case the client remains responsible for the data and we act as a processor on its behalf. We will:"], bullets: ["access only the data necessary to perform the agreed work;", "keep credentials in secure password managers and never commit them to public repositories;", "use production data for testing only when unavoidable, and anonymise it wherever possible;", "revoke access and delete project copies within a reasonable period after project completion, unless retention is agreed in writing;", "report any confirmed breach affecting client data without undue delay."] },
  { title: "9. International Data Transfers", paragraphs: ["Our providers may store or process data in countries other than your own, including outside India. Where required, we use appropriate safeguards such as contractual protections to ensure your data receives an adequate level of protection."] },
  { title: "10. Data Retention", paragraphs: ["We keep personal data only as long as necessary for the purposes described. Typical periods: enquiry and contact records up to 24 months after last contact; client engagement records for the duration of the contract and up to 8 years afterwards for tax and legal compliance; analytics data in aggregated or anonymised form; marketing subscriptions until you unsubscribe. We securely delete or anonymise data when it is no longer required."] },
  { title: "11. Data Security", paragraphs: ["We apply reasonable technical and organisational measures, including HTTPS/TLS encryption in transit, access controls and least-privilege permissions, multi-factor authentication on key accounts, regular software updates and dependency patching, and backups. No method of transmission or storage is completely secure, so we cannot guarantee absolute security."] },
  { title: "12. Your Rights", paragraphs: ["Subject to applicable law (including the DPDP Act 2023 in India, the GDPR/UK GDPR in Europe and the CCPA/CPRA in California), you may have the right to:"], bullets: ["access the personal data we hold about you and obtain a summary of it;", "correct inaccurate or incomplete data and request erasure of data no longer needed;", "withdraw consent at any time, without affecting earlier lawful processing;", "object to or restrict certain processing, and request data portability;", "nominate another person to exercise your rights in the event of death or incapacity (India);", "lodge a grievance with us or a complaint with your local data protection authority."], after: "To exercise any right, email privacy@siliconbrains.in. We may need to verify your identity and will respond within the period required by law, generally within 30 days." },
  { title: "13. Children's Privacy", paragraphs: ["The Website is intended for businesses and adults. We do not knowingly collect personal data from children under 18 without verifiable parental consent. If you believe a child has provided us data, contact us and we will delete it promptly."] },
  { title: "14. Do Not Track and Marketing Choices", paragraphs: ["We aim to respect browser Do Not Track and Global Privacy Control signals where technically feasible. Every marketing email includes an unsubscribe link."] },
  { title: "15. Changes to This Policy", paragraphs: ["We may update this Policy from time to time. The Effective Date at the top shows when it was last revised. Material changes will be highlighted on the Website or communicated by email. Continued use of the Website after an update means you accept the revised Policy."] },
  { title: "16. Grievance Officer and Contact", paragraphs: ["For questions, requests or grievances about this Policy or your personal data, contact the Privacy Officer at privacy@siliconbrains.in. The supplied policy lists Nagpur, India, 440034 as the address and states that requests are acknowledged within 72 hours and resolved within 30 days."] },
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
  { name: "Mohit Gurnule", role: "Chief Financial Officer", image: "/team/mohit-gurnule-portrait.jpeg" },
  { name: "Hemant Tripathi", role: "Project Manager", image: "/team/hemant-tripathi-portrait.jpeg" },
  { name: "Raj Pande", role: "Social Media Manager", image: "/team/raj-pande-portrait.jpeg" },
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
          <Button href="/" variant="secondary" size="sm" className="w-full justify-center min-[480px]:w-auto"><ArrowLeft size={14} /> Back to University</Button>
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
        </nav>

        <section id="privacy" className="mt-8 scroll-mt-24 rounded-2xl border border-cream-300 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-cream-200 pb-5">
            <div><p className="text-xs font-bold uppercase tracking-wide text-green-700">Document reference SB-PP-0001</p><h2 className="mt-1 font-heading text-2xl font-bold text-green-900">Privacy Policy</h2></div>
            <p className="rounded-full bg-cream-100 px-3 py-1 text-xs font-semibold text-ink-muted">Effective 13 October 2026</p>
          </div>
          <p className="mt-5 text-sm leading-7 text-ink-muted">This Privacy Policy explains how SiliconBrains (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) collects, uses, stores, shares and protects personal data when you visit www.siliconbrains.in (the &quot;Website&quot;), contact us, or engage us for web engineering services such as web application development, front-end and back-end engineering, API integration, performance optimisation, hosting and maintenance. By using the Website you acknowledge that you have read and understood this Policy.</p>
          <div className="mt-6">{privacySections.map((section) => <PolicySection key={section.title} section={section} />)}</div>
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
