"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken, getRole } from "@/lib/auth";

export default function Root() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
    } else {
      const role = getRole();
      if (role === "SUPER_ADMIN") {
        router.replace("/admin");
      } else {
        router.replace("/dashboard");
      }
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-indigo-500 animate-pulse text-sm font-semibold tracking-widest">
        LOADING MEDPORTAL...
      </div>
    </div>
  );
}
