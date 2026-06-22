"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Calendar,
  MessageSquare,
  Users,
  UserCheck,
  Plus,
  Trash2,
  Send,
  Search,
  Lock,
  Unlock,
  Check,
  CheckCheck,
  Clock,
  AlertCircle,
  X,
  Briefcase, 
  User, 
  Phone, 
  Mail, 
  Zap, 
  RefreshCw, 
  LogOut 
} from "lucide-react";
import { apiFetch as fetch, WS_BASE, API_BASE } from "@/lib/api";
import { clearAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

// Type definitions
interface Doctor {
  id: number;
  name: string;
  specialty: string;
  email?: string;
  phone_number?: string;
}

interface Patient {
  id: number;
  name: string;
  phone_number: string;
  email?: string;
  created_at: string;
  last_message?: {
    text: string;
    timestamp: string;
    status: string;
  };
}

interface TimeSlot {
  id: number;
  doctor_id: number;
  start_time: string;
  end_time: string;
  is_available: boolean;
  is_blocked: boolean;
  appointment?: {
    id: number;
    status: string;
    patient: {
      id: number;
      name: string;
      phone_number: string;
    };
  } | null;
}

interface Message {
  id: string;
  sender: string;
  recipient: string;
  text: string;
  status: string;
  timestamp: string;
  msg_type: string;
}

interface NlpLog {
  id: number;
  patient_phone: string;
  raw_message: string;
  llm_response: string | null;
  error_reason: string | null;
  created_at: string;
  reviewed: boolean;
}

export default function Dashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"calendar" | "inbox" | "patients" | "doctors" | "ai_logs">("calendar");
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Data State
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [timeslots, setTimeslots] = useState<TimeSlot[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState<number | "">("");
  const [selectedDate, setSelectedDate] = useState<string>("");
  
  // Doctor Panel State
  const [newDoctor, setNewDoctor] = useState({ name: "", specialty: "", email: "", phone_number: "" });
  const [showAddDoctor, setShowAddDoctor] = useState(false);
  
  // Slot Generation State
  const [genSlotsDocId, setGenSlotsDocId] = useState<number | "">("");
  const [genDate, setGenDate] = useState<string>("");
  const [genStartTime, setGenStartTime] = useState<string>("09:00");
  const [genEndTime, setGenEndTime] = useState<string>("17:00");
  const [genInterval, setGenInterval] = useState<number>(30); // minutes
  const [showGenModal, setShowGenModal] = useState(false);
  
  // Patient View State
  const [patientSearch, setPatientSearch] = useState<string>("");
  const [selectedPatientHistory, setSelectedPatientHistory] = useState<Patient | null>(null);
  const [patientHistoryMessages, setPatientHistoryMessages] = useState<Message[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // AI Review Queue
  const [nlpLogs, setNlpLogs] = useState<NlpLog[]>([]);

  // Inbox View State
  const [inboxChats, setInboxChats] = useState<Patient[]>([]);
  const [activeChat, setActiveChat] = useState<Patient | null>(null);
  const [activeChatMessages, setActiveChatMessages] = useState<Message[]>([]);
  const [replyText, setReplyText] = useState<string>("");
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // TimeSlot Detail Modal
  const [selectedSlotDetails, setSelectedSlotDetails] = useState<TimeSlot | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    let ws: WebSocket;
    
    function connectWS() {
      ws = new WebSocket(WS_BASE);
      
      ws.onopen = () => {
        setWsConnected(true);
        console.log("WebSocket connected to Portal Gateway");
      };
      
      ws.onclose = () => {
        setWsConnected(false);
        console.log("WebSocket disconnected. Reconnecting in 3 seconds...");
        setTimeout(connectWS, 3000);
      };
      
      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        ws.close();
      };
      
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const { event: eventName, data } = payload;
          console.log("WS received event:", eventName, data);
          
          if (eventName === "message_received") {
            const newMsg: Message = data;
            // 1. Play sound or notify
            // 2. Add message to active chat if it matches active patient
            const patientPhone = newMsg.sender === "Me (You)" ? newMsg.recipient : newMsg.sender;
            
            // Check if active chat matches this phone number
            setActiveChat((prevActiveChat) => {
              if (prevActiveChat) {
                const cleanActive = prevActiveChat.phone_number.replace("+", "").trim();
                const cleanMsgPhone = patientPhone.replace("+", "").trim();
                if (cleanActive === cleanMsgPhone || cleanActive.endsWith(cleanMsgPhone) || cleanMsgPhone.endsWith(cleanActive)) {
                  setActiveChatMessages((prevMsgs) => [...prevMsgs, newMsg]);
                }
              }
              return prevActiveChat;
            });
            
            // Also update history list if open
            setSelectedPatientHistory((prevHist) => {
              if (prevHist) {
                const cleanHist = prevHist.phone_number.replace("+", "").trim();
                const cleanMsgPhone = patientPhone.replace("+", "").trim();
                if (cleanHist === cleanMsgPhone || cleanHist.endsWith(cleanMsgPhone) || cleanMsgPhone.endsWith(cleanHist)) {
                  setPatientHistoryMessages((prevMsgs) => [...prevMsgs, newMsg]);
                }
              }
              return prevHist;
            });
            
            // Reload patient lists to update latest message details
            fetchPatients();
            fetchInboxChats();
          }
          
          if (eventName === "message_status_updated") {
            const { whatsapp_message_id, status } = data;
            // Update message status in current chat view
            setActiveChatMessages((prevMsgs) =>
              prevMsgs.map((m) => (m.id === whatsapp_message_id ? { ...m, status } : m))
            );
            setPatientHistoryMessages((prevMsgs) =>
              prevMsgs.map((m) => (m.id === whatsapp_message_id ? { ...m, status } : m))
            );
          }
          
          if (eventName === "appointment_booked" || eventName === "appointment_updated") {
            // Reload timeslots if calendar is showing
            fetchTimeslots();
          }
          
          if (eventName === "timeslot_updated" || eventName === "timeslot_created") {
            fetchTimeslots();
          }
        } catch (e) {
          console.error("Error parsing WS message:", e);
        }
      };
    }
    
    connectWS();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Set default selected date to today
  useEffect(() => {
    const today = new Date().toISOString().split("T")[0];
    setSelectedDate(today);
    setGenDate(today);
  }, []);

  // Fetch initial doctors & patients
  useEffect(() => {
    fetchDoctors();
    fetchPatients();
    fetchInboxChats();
  }, []);

  // Fetch timeslots whenever selectedDoctor or date changes
  useEffect(() => {
    fetchTimeslots();
  }, [selectedDoctorId, selectedDate]);

  // Scroll to bottom of chat when messages update
  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [activeChatMessages]);

  // --- API CALLS ---

  const fetchDoctors = async () => {
    try {
      const res = await fetch(`${API_BASE}/portal/doctors`);
      const data = await res.json();
      setDoctors(data);
      if (data.length > 0 && selectedDoctorId === "") {
        setSelectedDoctorId(data[0].id);
        setGenSlotsDocId(data[0].id);
      }
      setLoading(false);
    } catch (e) {
      console.error("Error fetching doctors:", e);
    }
  };

  const fetchPatients = async () => {
    try {
      const res = await fetch(`${API_BASE}/portal/patients?search=${patientSearch}`);
      const data = await res.json();
      setPatients(data);
    } catch (e) {
      console.error("Error fetching patients:", e);
    }
  };

  const fetchInboxChats = async () => {
    try {
      const res = await fetch(`${API_BASE}/portal/patients`);
      const data = await res.json();
      // Filter patients that have at least one message log (last_message is not null)
      const chats = data.filter((p: Patient) => p.last_message !== null);
      setInboxChats(chats);
    } catch (e) {
      console.error("Error fetching inbox chats:", e);
    }
  };

  const fetchTimeslots = async () => {
    if (!selectedDoctorId || !selectedDate) return;
    try {
      const res = await fetch(
        `${API_BASE}/portal/timeslots?doctor_id=${selectedDoctorId}&start_date=${selectedDate}`
      );
      const data = await res.json();
      setTimeslots(data);
    } catch (e) {
      console.error("Error fetching timeslots:", e);
    }
  };

  const fetchChatMessages = async (patient: Patient) => {
    try {
      const res = await fetch(`${API_BASE}/portal/patients/${patient.id}/history`);
      const data = await res.json();
      setActiveChatMessages(data);
    } catch (e) {
      console.error("Error fetching chat history:", e);
    }
  };

  const fetchPatientHistory = async (patient: Patient) => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/portal/patients/${patient.id}/history`);
      const data = await res.json();
      setPatientHistoryMessages(data);
      setSelectedPatientHistory(patient);
    } catch (e) {
      console.error("Error fetching patient history:", e);
    } finally {
      setHistoryLoading(false);
    }
  };

  const fetchNlpLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/portal/nlp-logs`);
      const data = await res.json();
      setNlpLogs(data);
    } catch (e) {
      console.error("Error fetching NLP logs:", e);
    }
  };

  const resolveNlpLog = async (logId: number) => {
    try {
      const res = await fetch(`${API_BASE}/portal/nlp-logs/${logId}/resolve`, { method: "PUT" });
      if (res.ok) {
        fetchNlpLogs();
      }
    } catch (e) {
      console.error("Error resolving NLP log:", e);
    }
  };

  // --- ACTIONS ---

  const handleAddDoctor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDoctor.name || !newDoctor.specialty) return;
    try {
      const res = await fetch(`${API_BASE}/portal/doctors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newDoctor)
      });
      if (res.ok) {
        setNewDoctor({ name: "", specialty: "", email: "", phone_number: "" });
        setShowAddDoctor(false);
        fetchDoctors();
      }
    } catch (e) {
      console.error("Error creating doctor:", e);
    }
  };

  const handleDeleteDoctor = async (id: number) => {
    if (!confirm("Are you sure you want to delete this doctor profile?")) return;
    try {
      const res = await fetch(`${API_BASE}/portal/doctors/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        if (selectedDoctorId === id) setSelectedDoctorId("");
        fetchDoctors();
      }
    } catch (e) {
      console.error("Error deleting doctor:", e);
    }
  };

  const handleBlockTimeslot = async (slotId: number, currentBlockedState: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/portal/timeslots/block`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          timeslot_id: slotId,
          is_blocked: !currentBlockedState
        })
      });
      if (res.ok) {
        fetchTimeslots();
        setSelectedSlotDetails(null);
      }
    } catch (e) {
      console.error("Error toggling timeslot block:", e);
    }
  };

  const handleGenerateSlots = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!genSlotsDocId || !genDate || !genStartTime || !genEndTime) return;
    
    // Parse times
    const [startHour, startMin] = genStartTime.split(":").map(Number);
    const [endHour, endMin] = genEndTime.split(":").map(Number);
    
    const baseDate = new Date(genDate);
    
    let current = new Date(baseDate);
    current.setHours(startHour, startMin, 0, 0);
    
    const endLimit = new Date(baseDate);
    endLimit.setHours(endHour, endMin, 0, 0);
    
    let createdCount = 0;
    while (current < endLimit) {
      const slotStart = new Date(current);
      const slotEnd = new Date(current.getTime() + genInterval * 60000);
      
      try {
        await fetch(`${API_BASE}/portal/timeslots`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            doctor_id: genSlotsDocId,
            start_time: slotStart.toISOString(),
            end_time: slotEnd.toISOString()
          })
        });
        createdCount++;
      } catch (err) {
        console.error("Error generating slot:", err);
      }
      
      current = slotEnd;
    }
    
    alert(`Generated ${createdCount} slots successfully!`);
    setShowGenModal(false);
    fetchTimeslots();
  };

  const handleSendManualReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeChat || !replyText.trim()) return;
    
    const payload = {
      phone_number: activeChat.phone_number,
      text: replyText.trim()
    };
    
    setReplyText("");
    
    try {
      const res = await fetch(`${API_BASE}/portal/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!data.success) {
        alert("Failed to send message: " + data.error);
      }
    } catch (e) {
      console.error("Error sending manual reply:", e);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "sent":
        return <Check className="w-3.5 h-3.5 text-zinc-400" />;
      case "delivered":
        return <CheckCheck className="w-3.5 h-3.5 text-zinc-400" />;
      case "read":
        return <CheckCheck className="w-3.5 h-3.5 text-sky-400" />;
      case "failed":
        return <AlertCircle className="w-3.5 h-3.5 text-rose-500" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-zinc-500" />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      
      {/* Side Navigation Bar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0">
        <div>
          {/* Header */}
          <div className="p-6 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-indigo-600 p-2 rounded-lg text-white shadow-lg shadow-indigo-600/30">
                <Briefcase className="w-5 h-5" />
              </div>
              <span className="font-bold text-lg tracking-wider text-indigo-400">MEDPORTAL</span>
            </div>
            <button
              onClick={() => {
                clearAuth();
                router.push("/login");
              }}
              className="text-slate-400 hover:text-rose-400 transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
          
          {/* Real-time Status Badge */}
          <div className="mx-4 my-4 p-3 bg-slate-950/40 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Real-Time Sync</span>
            <span className={`flex items-center text-xs font-semibold ${wsConnected ? 'text-emerald-400' : 'text-rose-400 animate-pulse'}`}>
              <Zap className={`w-3.5 h-3.5 mr-1 ${wsConnected ? 'fill-emerald-400/20' : ''}`} />
              {wsConnected ? "Live" : "Connecting..."}
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="px-4 space-y-1">
            <button
              onClick={() => setActiveTab("calendar")}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                activeTab === "calendar"
                  ? "bg-indigo-600/90 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`}
            >
              <Calendar className="w-5 h-5 mr-3 shrink-0" />
              Calendar Grid
            </button>
            <button
              onClick={() => {
                setActiveTab("inbox");
                fetchInboxChats();
              }}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                activeTab === "inbox"
                  ? "bg-indigo-600/90 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`}
            >
              <MessageSquare className="w-5 h-5 mr-3 shrink-0" />
              Omnichannel Inbox
            </button>
            <button
              onClick={() => {
                setActiveTab("patients");
                fetchPatients();
              }}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                activeTab === "patients"
                  ? "bg-indigo-600/90 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`}
            >
              <Users className="w-5 h-5 mr-3 shrink-0" />
              Patient Database
            </button>
            <button
              onClick={() => setActiveTab("doctors")}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                activeTab === "doctors"
                  ? "bg-indigo-600/90 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`}
            >
              <UserCheck className="w-5 h-5 mr-3 shrink-0" />
              Doctor Panel
            </button>
            <button
              onClick={() => {
                setActiveTab("ai_logs");
                fetchNlpLogs();
              }}
              className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                activeTab === "ai_logs"
                  ? "bg-rose-600/90 text-white shadow-md shadow-rose-600/20"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`}
            >
              <Zap className="w-5 h-5 mr-3 shrink-0" />
              AI Review Queue
            </button>
          </nav>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 text-xs text-slate-500 text-center">
          Clinic Dashboard v1.1.0
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
        
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-4">
            <RefreshCw className="w-10 h-10 text-indigo-500 animate-spin" />
            <p className="text-slate-400 text-sm">Loading clinic database configurations...</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            
            {/* 1. CALENDAR GRID VIEW */}
            {activeTab === "calendar" && (
              <div className="flex-1 flex flex-col p-8 overflow-y-auto space-y-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
                  <div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">Interactive Calendar Grid</h1>
                    <p className="text-slate-400 text-sm">Monitor doctor timeslots, block vacations, and check booked appointments.</p>
                  </div>
                  
                  <div className="flex items-center space-x-3 bg-slate-900 p-2.5 rounded-2xl border border-slate-800 shadow-sm">
                    {/* Doctor Dropdown */}
                    <div className="flex flex-col">
                      <label className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 pl-1">Doctor</label>
                      <select
                        value={selectedDoctorId}
                        onChange={(e) => setSelectedDoctorId(Number(e.target.value))}
                        className="bg-slate-950 border border-slate-800 text-sm text-slate-100 px-3 py-1.5 rounded-xl outline-none focus:border-indigo-500 transition-colors"
                      >
                        {doctors.map((doc) => (
                          <option key={doc.id} value={doc.id}>
                            {doc.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    
                    {/* Date Selector */}
                    <div className="flex flex-col">
                      <label className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 pl-1">Date</label>
                      <input
                        type="date"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="bg-slate-950 border border-slate-800 text-sm text-slate-100 px-3 py-1.5 rounded-xl outline-none focus:border-indigo-500 transition-colors"
                      />
                    </div>

                    {/* Batch Generate Button */}
                    <button
                      onClick={() => {
                        setGenSlotsDocId(selectedDoctorId);
                        setGenDate(selectedDate);
                        setShowGenModal(true);
                      }}
                      className="mt-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl flex items-center transition-colors shadow-lg shadow-indigo-600/10"
                    >
                      <Plus className="w-3.5 h-3.5 mr-1" />
                      Bulk Slots
                    </button>
                  </div>
                </div>

                {/* Calendar Grid Color Labels */}
                <div className="flex items-center space-x-6 text-xs text-slate-400 bg-slate-900/50 p-4 rounded-xl border border-slate-800/65">
                  <span className="font-semibold text-slate-300 mr-2">Color Key:</span>
                  <span className="flex items-center"><span className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500/40 mr-1.5"></span>Free / Available</span>
                  <span className="flex items-center"><span className="w-3 h-3 rounded-full bg-indigo-500/20 border border-indigo-500/40 mr-1.5"></span>Booked (Active)</span>
                  <span className="flex items-center"><span className="w-3 h-3 rounded-full bg-rose-500/20 border border-rose-500/40 mr-1.5"></span>Blocked / Holiday</span>
                  <span className="flex items-center"><span className="w-3 h-3 rounded-full bg-slate-700/20 border border-slate-700/40 mr-1.5"></span>Completed</span>
                  <span className="flex items-center"><span className="w-3 h-3 rounded-full bg-amber-500/20 border border-amber-500/40 mr-1.5"></span>No Show</span>
                </div>

                {/* Grid */}
                {timeslots.length === 0 ? (
                  <div className="flex-1 py-20 flex flex-col items-center justify-center bg-slate-900/40 rounded-2xl border border-slate-850 border-dashed">
                    <Calendar className="w-12 h-12 text-slate-600 mb-3" />
                    <h3 className="text-slate-300 font-semibold mb-1">No timeslots exist for this date</h3>
                    <p className="text-slate-500 text-sm text-center max-w-sm">
                      Click the "Bulk Slots" button above to quickly generate slots for this doctor.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {timeslots.map((slot) => {
                      let colorClasses = "";
                      let statusText = "Free";
                      
                      if (slot.is_blocked) {
                        colorClasses = "bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20";
                        statusText = "Blocked (Holiday)";
                      } else if (slot.is_available) {
                        colorClasses = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20";
                        statusText = "Available";
                      } else if (slot.appointment) {
                        const status = slot.appointment.status;
                        if (status === "scheduled" || status === "confirmed") {
                          colorClasses = "bg-indigo-500/10 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/20";
                          statusText = `Booked (${status})`;
                        } else if (status === "completed") {
                          colorClasses = "bg-slate-700/20 text-slate-400 border-slate-700/30";
                          statusText = "Completed";
                        } else if (status === "no_show") {
                          colorClasses = "bg-amber-500/10 text-amber-400 border-amber-500/30";
                          statusText = "No Show";
                        } else {
                          colorClasses = "bg-purple-500/10 text-purple-400 border-purple-500/30";
                          statusText = status.toUpperCase();
                        }
                      } else {
                        colorClasses = "bg-slate-700/20 text-slate-400 border-slate-700/30";
                        statusText = "Booked (Details Unknown)";
                      }

                      const start = new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                      const end = new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                      return (
                        <div
                          key={slot.id}
                          onClick={() => setSelectedSlotDetails(slot)}
                          className={`p-4 rounded-2xl border ${colorClasses} cursor-pointer transition-all duration-200 flex flex-col justify-between h-32 hover:scale-[1.02] shadow-sm`}
                        >
                          <div>
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="font-bold text-base tracking-tight">{start} - {end}</span>
                              {slot.is_blocked && <Lock className="w-3.5 h-3.5 text-rose-400" />}
                            </div>
                            <span className="text-xs opacity-80 font-medium bg-slate-950/20 px-2 py-0.5 rounded-full inline-block">
                              {statusText}
                            </span>
                          </div>
                          
                          {slot.appointment && (
                            <div className="mt-2 text-xs font-semibold truncate border-t border-slate-500/10 pt-2 flex items-center">
                              <User className="w-3 h-3 mr-1 opacity-80" />
                              {slot.appointment.patient.name}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* 2. OMNICHANNEL INBOX VIEW */}
            {activeTab === "inbox" && (
              <div className="flex-1 flex overflow-hidden">
                {/* Inbox Left Sidebar - Recent Chats */}
                <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0">
                  <div className="p-4 border-b border-slate-800">
                    <h2 className="text-lg font-bold text-white mb-3">Conversations</h2>
                    <div className="relative">
                      <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                      <input
                        type="text"
                        placeholder="Filter chats..."
                        value={patientSearch}
                        onChange={(e) => setPatientSearch(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                      />
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto divide-y divide-slate-800/40">
                    {inboxChats.length === 0 ? (
                      <div className="p-8 text-center text-slate-500 text-sm">
                        No active WhatsApp threads found.
                      </div>
                    ) : (
                      inboxChats
                        .filter(chat => 
                          chat.name.toLowerCase().includes(patientSearch.toLowerCase()) ||
                          chat.phone_number.includes(patientSearch)
                        )
                        .map((chat) => {
                          const isActive = activeChat && activeChat.id === chat.id;
                          return (
                            <div
                              key={chat.id}
                              onClick={async () => {
                                setActiveChat(chat);
                                await fetchChatMessages(chat);
                              }}
                              className={`p-4 cursor-pointer transition-all duration-200 flex flex-col hover:bg-slate-800/40 ${
                                isActive ? "bg-slate-800/70 border-l-4 border-indigo-500 pl-3" : ""
                              }`}
                            >
                              <div className="flex justify-between items-start mb-1">
                                <span className="font-bold text-sm text-slate-200">{chat.name}</span>
                                <span className="text-[10px] text-slate-500">
                                  {chat.last_message?.timestamp 
                                    ? new Date(chat.last_message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                    : ""}
                                </span>
                              </div>
                              <div className="text-xs text-slate-400 truncate pr-6 font-medium">
                                {chat.last_message?.text || "Media attachments received"}
                              </div>
                              <div className="flex justify-between items-center mt-2">
                                <span className="text-[10px] text-slate-500 tracking-tight font-semibold flex items-center">
                                  <Phone className="w-2.5 h-2.5 mr-1" />
                                  {chat.phone_number}
                                </span>
                                {chat.last_message && chat.last_message.status && (
                                  <span>{getStatusIcon(chat.last_message.status)}</span>
                                )}
                              </div>
                            </div>
                          );
                        })
                    )}
                  </div>
                </div>

                {/* Inbox Right Sidebar - Active Chat details & input */}
                <div className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
                  {activeChat ? (
                    <div className="flex-1 flex flex-col overflow-hidden">
                      {/* Chat Header */}
                      <div className="p-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
                        <div>
                          <h3 className="font-bold text-white">{activeChat.name}</h3>
                          <p className="text-xs text-slate-400 flex items-center mt-0.5">
                            <Phone className="w-3 h-3 mr-1 text-slate-500" />
                            {activeChat.phone_number}
                          </p>
                        </div>
                        
                        <button
                          onClick={() => fetchChatMessages(activeChat)}
                          className="bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded-xl transition-colors border border-slate-705"
                          title="Refresh Messages"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Messages Area */}
                      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-950/40">
                        {activeChatMessages.map((msg) => {
                          const isMe = msg.sender === "Me (You)";
                          return (
                            <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                              <div
                                className={`max-w-[70%] rounded-2xl px-4 py-3 text-sm shadow-md border ${
                                  isMe
                                    ? "bg-indigo-600 text-white border-indigo-500/20 rounded-tr-none"
                                    : "bg-slate-800 text-slate-100 border-slate-700/60 rounded-tl-none"
                                }`}
                              >
                                {/* Media / Text formatting rendering */}
                                {msg.text.includes("<img") ? (
                                  <div 
                                    className="rounded-lg overflow-hidden my-1" 
                                    dangerouslySetInnerHTML={{ __html: msg.text }} 
                                  />
                                ) : (
                                  <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                                )}
                                
                                <div className="mt-1.5 flex items-center justify-end space-x-1.5 text-[10px] opacity-75">
                                  <span>
                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                  </span>
                                  {isMe && <span>{getStatusIcon(msg.status)}</span>}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                        <div ref={chatBottomRef} />
                      </div>

                      {/* Chat Input Footer */}
                      <form onSubmit={handleSendManualReply} className="p-4 bg-slate-900 border-t border-slate-800 flex items-center space-x-3">
                        <input
                          type="text"
                          value={replyText}
                          onChange={(e) => setReplyText(e.target.value)}
                          placeholder="Type a manual WhatsApp message to send via Meta Cloud API..."
                          className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                        />
                        <button
                          type="submit"
                          disabled={!replyText.trim()}
                          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white p-3 rounded-xl transition-all duration-200 shadow-md shadow-indigo-600/10 flex items-center justify-center shrink-0"
                        >
                          <Send className="w-4.5 h-4.5" />
                        </button>
                      </form>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8">
                      <MessageSquare className="w-16 h-16 text-slate-800 mb-4" />
                      <h3 className="text-lg font-bold text-slate-400">No Chat Selected</h3>
                      <p className="text-sm text-slate-500 text-center max-w-sm mt-1">
                        Select a patient conversation thread on the left pane to view message logs and send manual staff replies.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 3. PATIENTS DATABASE VIEW */}
            {activeTab === "patients" && (
              <div className="flex-1 flex flex-col p-8 overflow-y-auto space-y-6">
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">Patient Database</h1>
                  <p className="text-slate-400 text-sm">Search clinical patient profiles and click through to inspect their full conversation histories.</p>
                </div>

                {/* Filter and Search Bar */}
                <div className="flex space-x-4">
                  <div className="relative flex-1 max-w-md">
                    <Search className="w-5 h-5 text-slate-500 absolute left-3 top-3" />
                    <input
                      type="text"
                      placeholder="Search patient by name or WhatsApp phone number..."
                      value={patientSearch}
                      onChange={(e) => setPatientSearch(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                    />
                  </div>
                  <button
                    onClick={fetchPatients}
                    className="bg-slate-900 hover:bg-slate-850 text-slate-200 border border-slate-800 rounded-xl px-4 py-2.5 text-sm transition-all duration-200 flex items-center"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Search
                  </button>
                </div>

                {/* Patient Grid / Table */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-950 border-b border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-400">
                        <th className="p-4">Name</th>
                        <th className="p-4">WhatsApp Number</th>
                        <th className="p-4">Email Address</th>
                        <th className="p-4">Registered On</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40 text-sm">
                      {patients.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="p-8 text-center text-slate-500">
                            No patient profiles matched your query.
                          </td>
                        </tr>
                      ) : (
                        patients.map((pat) => (
                          <tr key={pat.id} className="hover:bg-slate-850/30 transition-colors">
                            <td className="p-4 font-bold text-white flex items-center space-x-2">
                              <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs uppercase">
                                {pat.name.slice(0, 2)}
                              </div>
                              <span>{pat.name}</span>
                            </td>
                            <td className="p-4 font-mono text-slate-300">{pat.phone_number}</td>
                            <td className="p-4 text-slate-400">{pat.email || "—"}</td>
                            <td className="p-4 text-slate-400">
                              {new Date(pat.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                            </td>
                            <td className="p-4 text-right">
                              <button
                                onClick={() => fetchPatientHistory(pat)}
                                className="bg-indigo-600/10 hover:bg-indigo-600 border border-indigo-500/20 text-indigo-400 hover:text-white text-xs font-bold px-3 py-1.5 rounded-xl transition-all duration-200"
                              >
                                View Chat Log
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 4. DOCTORS PANEL VIEW */}
            {activeTab === "doctors" && (
              <div className="flex-1 flex flex-col p-8 overflow-y-auto space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">Doctor profiles</h1>
                    <p className="text-slate-400 text-sm">Manage staff doctor accounts, active hours configurations, and holiday blocks.</p>
                  </div>
                  
                  <button
                    onClick={() => setShowAddDoctor(!showAddDoctor)}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-4 py-2.5 rounded-xl flex items-center transition-colors shadow-lg shadow-indigo-600/10"
                  >
                    <Plus className="w-4 h-4 mr-1.5" />
                    Add Doctor Profile
                  </button>
                </div>

                {/* Add Doctor Form Toggle */}
                {showAddDoctor && (
                  <form onSubmit={handleAddDoctor} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4 shadow-xl max-w-xl">
                    <h3 className="font-bold text-lg text-white">New Doctor Account</h3>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="flex flex-col space-y-1">
                        <label className="text-xs text-slate-400 font-medium pl-1">Doctor Name</label>
                        <input
                          type="text"
                          placeholder="e.g. Dr. Jane Foster"
                          value={newDoctor.name}
                          onChange={(e) => setNewDoctor({ ...newDoctor, name: e.target.value })}
                          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                          required
                        />
                      </div>
                      
                      <div className="flex flex-col space-y-1">
                        <label className="text-xs text-slate-400 font-medium pl-1">Specialty</label>
                        <input
                          type="text"
                          placeholder="e.g. Dermatology"
                          value={newDoctor.specialty}
                          onChange={(e) => setNewDoctor({ ...newDoctor, specialty: e.target.value })}
                          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                          required
                        />
                      </div>
                      
                      <div className="flex flex-col space-y-1">
                        <label className="text-xs text-slate-400 font-medium pl-1">Email Address</label>
                        <input
                          type="email"
                          placeholder="foster@clinic.com"
                          value={newDoctor.email}
                          onChange={(e) => setNewDoctor({ ...newDoctor, email: e.target.value })}
                          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                        />
                      </div>
                      
                      <div className="flex flex-col space-y-1">
                        <label className="text-xs text-slate-400 font-medium pl-1">Office Phone Number</label>
                        <input
                          type="text"
                          placeholder="+12345"
                          value={newDoctor.phone_number}
                          onChange={(e) => setNewDoctor({ ...newDoctor, phone_number: e.target.value })}
                          className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-200 transition-colors"
                        />
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 pt-2">
                      <button
                        type="submit"
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-md"
                      >
                        Register Account
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowAddDoctor(false)}
                        className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors border border-slate-705"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                {/* Doctors Grid list */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {doctors.map((doc) => (
                    <div key={doc.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between space-y-4 shadow-lg hover:border-slate-700/80 transition-all duration-200">
                      <div>
                        <div className="flex items-center justify-between">
                          <h3 className="font-bold text-white text-lg">{doc.name}</h3>
                          <span className="text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                            {doc.specialty}
                          </span>
                        </div>
                        
                        <div className="mt-4 space-y-2 text-xs text-slate-400">
                          <p className="flex items-center">
                            <Mail className="w-3.5 h-3.5 mr-2 text-slate-500" />
                            {doc.email || "No email assigned"}
                          </p>
                          <p className="flex items-center">
                            <Phone className="w-3.5 h-3.5 mr-2 text-slate-500" />
                            {doc.phone_number || "No contact number assigned"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center justify-end pt-4 border-t border-slate-800/40">
                        <button
                          onClick={() => handleDeleteDoctor(doc.id)}
                          className="text-rose-500 hover:bg-rose-500/10 p-2 rounded-xl border border-transparent hover:border-rose-500/20 transition-all duration-200 flex items-center text-xs font-semibold"
                          title="Delete Doctor Profile"
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          Delete Profile
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* 5. AI LOGS QUEUE */}
            {activeTab === "ai_logs" && (
              <div className="flex-1 flex flex-col p-8 overflow-y-auto space-y-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
                  <div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">AI Review Queue</h1>
                    <p className="text-slate-400 text-sm">Review incoming unstructured messages that our AI failed to parse.</p>
                  </div>
                  <button
                    onClick={fetchNlpLogs}
                    className="bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded-xl transition-colors border border-slate-700 flex items-center"
                    title="Refresh Logs"
                  >
                    <RefreshCw className="w-5 h-5" />
                  </button>
                </div>

                <div className="flex-1">
                  {nlpLogs.length === 0 ? (
                    <div className="py-20 flex flex-col items-center justify-center bg-slate-900/40 rounded-2xl border border-slate-850 border-dashed">
                      <Zap className="w-12 h-12 text-slate-600 mb-3" />
                      <h3 className="text-slate-300 font-semibold mb-1">Queue is Empty</h3>
                      <p className="text-slate-500 text-sm text-center max-w-sm">
                        All NLP parsing was successful. No manual reviews needed!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {nlpLogs.map((log) => (
                        <div key={log.id} className={`p-4 rounded-xl border flex flex-col space-y-3 transition-colors ${log.reviewed ? "bg-slate-900/30 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/30"}`}>
                          <div className="flex items-start justify-between">
                            <div>
                              <span className="font-bold text-white block mb-1">From: {log.patient_phone}</span>
                              <span className="text-xs text-slate-400">Received: {new Date(log.created_at).toLocaleString()}</span>
                            </div>
                            {!log.reviewed ? (
                              <button 
                                onClick={() => resolveNlpLog(log.id)}
                                className="text-xs bg-rose-500 hover:bg-rose-600 text-white px-3 py-1.5 rounded-lg shadow-sm transition-colors"
                              >
                                Mark as Resolved
                              </button>
                            ) : (
                              <span className="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                                Resolved
                              </span>
                            )}
                          </div>
                          
                          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                            <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Raw Message</span>
                            <p className="text-sm text-slate-200 break-words">{log.raw_message}</p>
                          </div>
                          
                          <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800/50">
                            <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Parse Error</span>
                            <p className="text-xs text-rose-400 font-mono">{log.error_reason}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            
          </div>
        )}
      </main>

      {/* --- DIALOG MODALS --- */}

      {/* 1. TIMESLOT DETAILS MODAL */}
      {selectedSlotDetails && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl w-full max-w-md shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-lg text-white">Timeslot Details</h3>
              <button
                onClick={() => setSelectedSlotDetails(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Time Range:</span>
                <span className="font-semibold text-white">
                  {new Date(selectedSlotDetails.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {" "}
                  {new Date(selectedSlotDetails.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Date:</span>
                <span className="font-semibold text-white">
                  {new Date(selectedSlotDetails.start_time).toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              </div>
              
              <div className="border-t border-slate-800/60 my-2 pt-2">
                {selectedSlotDetails.appointment ? (
                  <div className="space-y-2.5">
                    <span className="text-xs uppercase font-bold text-indigo-400 tracking-wider">Active Patient Appointment</span>
                    <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-400">Patient:</span>
                        <span className="text-xs font-bold text-white">{selectedSlotDetails.appointment.patient.name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-400">WhatsApp:</span>
                        <span className="text-xs font-mono text-white">{selectedSlotDetails.appointment.patient.phone_number}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-400">Booking Status:</span>
                        <span className="text-xs font-semibold text-indigo-400 capitalize bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                          {selectedSlotDetails.appointment.status}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-2 text-slate-400 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1.5 text-slate-500" />
                    No patient booking scheduled.
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-3 pt-4 border-t border-slate-800/60">
              {!selectedSlotDetails.appointment && (
                <button
                  onClick={() => handleBlockTimeslot(selectedSlotDetails.id, selectedSlotDetails.is_blocked)}
                  className={`flex-1 flex items-center justify-center font-semibold text-xs py-2 px-3 rounded-xl transition-all duration-200 ${
                    selectedSlotDetails.is_blocked
                      ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                      : "bg-rose-600 hover:bg-rose-500 text-white"
                  }`}
                >
                  {selectedSlotDetails.is_blocked ? (
                    <>
                      <Unlock className="w-3.5 h-3.5 mr-1" />
                      Unblock Timeslot
                    </>
                  ) : (
                    <>
                      <Lock className="w-3.5 h-3.5 mr-1" />
                      Block (Vacation)
                    </>
                  )}
                </button>
              )}
              <button
                onClick={() => setSelectedSlotDetails(null)}
                className="flex-1 bg-slate-850 hover:bg-slate-800 text-slate-300 font-semibold text-xs py-2 px-3 rounded-xl transition-colors border border-slate-750"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. PATIENT HISTORY MODAL */}
      {selectedPatientHistory && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 shrink-0">
              <div>
                <h3 className="font-bold text-lg text-white">Conversation History</h3>
                <p className="text-xs text-indigo-400 font-medium">{selectedPatientHistory.name} ({selectedPatientHistory.phone_number})</p>
              </div>
              <button
                onClick={() => setSelectedPatientHistory(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto my-4 p-4 bg-slate-950 rounded-xl space-y-3 min-h-[300px]">
              {historyLoading ? (
                <div className="h-full flex items-center justify-center">
                  <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
                </div>
              ) : patientHistoryMessages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                  No text exchanges logged with this patient phone number.
                </div>
              ) : (
                patientHistoryMessages.map((msg) => {
                  const isMe = msg.sender === "Me (You)";
                  return (
                    <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-xs shadow-md border ${
                          isMe
                            ? "bg-indigo-600 text-white border-indigo-500/20 rounded-tr-none"
                            : "bg-slate-800 text-slate-100 border-slate-700/60 rounded-tl-none"
                        }`}
                      >
                        {msg.text.includes("<img") ? (
                          <div 
                            className="rounded-lg overflow-hidden my-1" 
                            dangerouslySetInnerHTML={{ __html: msg.text }} 
                          />
                        ) : (
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                        )}
                        <div className="mt-1 flex items-center justify-end space-x-1 text-[9px] opacity-75">
                          <span>
                            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          {isMe && <span>{getStatusIcon(msg.status)}</span>}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="shrink-0 flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => {
                  // Quick reply redirect
                  setSelectedPatientHistory(null);
                  setActiveChat(selectedPatientHistory);
                  setActiveTab("inbox");
                  fetchChatMessages(selectedPatientHistory);
                }}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs py-2 px-4 rounded-xl transition-colors shadow-md shadow-indigo-600/10"
              >
                Open in Chat Inbox
              </button>
              <button
                onClick={() => setSelectedPatientHistory(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs py-2 px-4 rounded-xl transition-colors border border-slate-750"
              >
                Close Logs
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. BULK SLOTS GENERATION MODAL */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleGenerateSlots} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl w-full max-w-md shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-lg text-white">Generate Doctor Timeslots</h3>
              <button
                type="button"
                onClick={() => setShowGenModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex flex-col space-y-1">
                <label className="text-xs text-slate-400 font-medium pl-1">Select Doctor</label>
                <select
                  value={genSlotsDocId}
                  onChange={(e) => setGenSlotsDocId(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-100 transition-colors"
                  required
                >
                  <option value="">-- Select Doctor --</option>
                  {doctors.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col space-y-1">
                <label className="text-xs text-slate-400 font-medium pl-1">Date</label>
                <input
                  type="date"
                  value={genDate}
                  onChange={(e) => setGenDate(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-100 transition-colors"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col space-y-1">
                  <label className="text-xs text-slate-400 font-medium pl-1">Shift Start Time</label>
                  <input
                    type="time"
                    value={genStartTime}
                    onChange={(e) => setGenStartTime(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-100 transition-colors"
                    required
                  />
                </div>

                <div className="flex flex-col space-y-1">
                  <label className="text-xs text-slate-400 font-medium pl-1">Shift End Time</label>
                  <input
                    type="time"
                    value={genEndTime}
                    onChange={(e) => setGenEndTime(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-100 transition-colors"
                    required
                  />
                </div>
              </div>

              <div className="flex flex-col space-y-1">
                <label className="text-xs text-slate-400 font-medium pl-1">Slot Interval (minutes)</label>
                <select
                  value={genInterval}
                  onChange={(e) => setGenInterval(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none focus:border-indigo-500 text-slate-100 transition-colors"
                  required
                >
                  <option value={15}>15 Minutes</option>
                  <option value={30}>30 Minutes</option>
                  <option value={60}>60 Minutes (1 Hour)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center space-x-3 pt-4 border-t border-slate-800/60">
              <button
                type="submit"
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs py-2 px-3 rounded-xl transition-all duration-200 shadow-md shadow-indigo-600/10"
              >
                Generate Timeslots
              </button>
              <button
                type="button"
                onClick={() => setShowGenModal(false)}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs py-2 px-3 rounded-xl transition-colors border border-slate-750"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

    </div>
  );
}
