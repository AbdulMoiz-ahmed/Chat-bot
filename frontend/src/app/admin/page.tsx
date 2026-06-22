"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { clearAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { LogOut, Shield, Building, UserPlus, AlertCircle, CheckCircle } from "lucide-react";

export default function AdminDashboard() {
  const router = useRouter();
  const [clinicName, setClinicName] = useState("");
  const [waPhoneNumberId, setWaPhoneNumberId] = useState("");
  
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [clinicId, setClinicId] = useState("");

  const [message, setMessage] = useState<{type: "error"|"success", text: string} | null>(null);

  const handleCreateClinic = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      const res = await apiFetch("/admin/clinics", {
        method: "POST",
        body: JSON.stringify({ name: clinicName, wa_phone_number_id: waPhoneNumberId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create clinic");
      setMessage({ type: "success", text: `Clinic created successfully with ID: ${data.id}` });
      setClinicName("");
      setWaPhoneNumberId("");
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      const res = await apiFetch("/admin/users", {
        method: "POST",
        body: JSON.stringify({ email: adminEmail, password: adminPassword, clinic_id: parseInt(clinicId) })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create admin");
      setMessage({ type: "success", text: `Admin created successfully with ID: ${data.id}` });
      setAdminEmail("");
      setAdminPassword("");
      setClinicId("");
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        <div className="flex items-center justify-between border-b border-slate-800 pb-6">
          <div className="flex items-center space-x-4">
            <div className="bg-indigo-600 p-3 rounded-xl shadow-lg shadow-indigo-600/30">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Super Admin Portal</h1>
              <p className="text-slate-400">Manage tenants and clinic administrators</p>
            </div>
          </div>
          <button
            onClick={() => { clearAuth(); router.push("/login"); }}
            className="flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 px-4 py-2 rounded-xl transition-colors"
          >
            <LogOut className="w-4 h-4 text-rose-400" />
            <span className="text-sm font-semibold text-rose-400">Logout</span>
          </button>
        </div>

        {message && (
          <div className={`p-4 rounded-xl flex items-center space-x-3 ${message.type === "error" ? "bg-rose-500/10 border border-rose-500/30 text-rose-400" : "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"}`}>
            {message.type === "error" ? <AlertCircle className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
            <span className="font-semibold text-sm">{message.text}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Create Clinic Form */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center space-x-3 mb-6 border-b border-slate-800 pb-4">
              <Building className="w-6 h-6 text-indigo-400" />
              <h2 className="text-xl font-bold">Register New Clinic</h2>
            </div>
            <form onSubmit={handleCreateClinic} className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">Clinic Name</label>
                <input required value={clinicName} onChange={(e) => setClinicName(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 outline-none focus:border-indigo-500 text-slate-200" placeholder="Acme Clinic" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">WhatsApp Phone ID</label>
                <input required value={waPhoneNumberId} onChange={(e) => setWaPhoneNumberId(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 outline-none focus:border-indigo-500 text-slate-200" placeholder="123456789012345" />
              </div>
              <button type="submit" className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-600/20 active:scale-[0.98]">Register Tenant</button>
            </form>
          </div>

          {/* Create Admin Form */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center space-x-3 mb-6 border-b border-slate-800 pb-4">
              <UserPlus className="w-6 h-6 text-emerald-400" />
              <h2 className="text-xl font-bold">Provision Clinic Admin</h2>
            </div>
            <form onSubmit={handleCreateAdmin} className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">Admin Email</label>
                <input type="email" required value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 outline-none focus:border-emerald-500 text-slate-200" placeholder="admin@acme.com" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">Password</label>
                <input type="password" required value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 outline-none focus:border-emerald-500 text-slate-200" placeholder="••••••••" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">Clinic ID</label>
                <input type="number" required value={clinicId} onChange={(e) => setClinicId(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 outline-none focus:border-emerald-500 text-slate-200" placeholder="1" />
              </div>
              <button type="submit" className="w-full mt-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-600/20 active:scale-[0.98]">Provision User</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
