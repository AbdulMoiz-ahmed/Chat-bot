export const setToken = (token: string, role: string, clinicId?: number | null) => {
  if (typeof window !== "undefined") {
    localStorage.setItem("token", token);
    localStorage.setItem("role", role);
    if (clinicId !== undefined && clinicId !== null) {
      localStorage.setItem("clinic_id", clinicId.toString());
    } else {
      localStorage.removeItem("clinic_id");
    }
  }
};

export const getToken = () => {
  if (typeof window !== "undefined") {
    return localStorage.getItem("token");
  }
  return null;
};

export const getRole = () => {
  if (typeof window !== "undefined") {
    return localStorage.getItem("role");
  }
  return null;
};

export const clearAuth = () => {
  if (typeof window !== "undefined") {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("clinic_id");
  }
};
