"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function AboutBackButton() {
  const router = useRouter();

  function goBack() {
    if (window.history.length > 1) {
      router.back();
      return;
    }

    router.push("/");
  }

  return (
    <Button
      type="button"
      onClick={goBack}
      variant="secondary"
      size="sm"
      className="w-full justify-center min-[480px]:w-auto"
    >
      <ArrowLeft size={14} /> Back
    </Button>
  );
}
