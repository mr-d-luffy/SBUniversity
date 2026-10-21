import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="page-enter grid min-h-dvh place-items-center px-4 text-center">
      <div>
        <p className="font-heading text-6xl font-bold text-green-700">404</p>
        <h1 className="mt-2 text-xl">We couldn&apos;t find that page</h1>
        <p className="mt-1 text-ink-muted">Check the address or head back to the start.</p>
        <Button href="/" variant="primary" className="mt-6">Go home</Button>
      </div>
    </div>
  );
}
