"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { API_URL } from "../config";

interface User {
  id?: number;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  // Load token and restore session on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("pulseguard_token");
    const savedUserEmail = localStorage.getItem("pulseguard_user_email");

    if (savedToken && savedUserEmail) {
      setToken(savedToken);
      setUser({ email: savedUserEmail });
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Authentication failed. Please check your credentials.");
      }

      const data = await response.json();
      const accessToken = data.access_token;

      localStorage.setItem("pulseguard_token", accessToken);
      localStorage.setItem("pulseguard_user_email", email);

      setToken(accessToken);
      setUser({ email });
      
      router.push("/dashboard");
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [router]);

  const signup = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Registration failed. Email might already be taken.");
      }

      // Automatically login user after successful signup
      await login(email, password);
    } catch (error) {
      console.error("Signup error:", error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem("pulseguard_token");
    localStorage.removeItem("pulseguard_user_email");
    setToken(null);
    setUser(null);
    router.push("/auth/login");
  }, [router]);

  const contextValue = useMemo(() => ({
    user,
    token,
    loading,
    isAuthenticated: !!token,
    login,
    signup,
    logout,
  }), [user, token, loading, login, signup, logout]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
