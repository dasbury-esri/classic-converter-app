import React, { createContext, useContext, useEffect, useState } from "react";
import { UserSession } from "@esri/arcgis-rest-auth";

const clientId = "9Mtt4klv5XPptTIK";
const redirectUri = "http://localhost:5173";
const SESSION_KEY = "arcgis_session";

type AuthContextType = {
  session: UserSession | null;
  token: string | null;
  signIn: () => void;
  signOut: () => void;
  loading: boolean;
};

const AuthContext = createContext<AuthContextType>({
  session: null,
  token: null,
  signIn: () => {},
  signOut: () => {},
  loading: false,
});

export const useAuth = () => useContext(AuthContext);

function saveSession(session: UserSession) {
  try {
    const serialized = session.serialize();
    sessionStorage.setItem(SESSION_KEY, serialized);
  } catch (error) {
    console.warn("Could not serialize session:", error);
  }
}

function restoreSession(): UserSession | null {
  const serialized = sessionStorage.getItem(SESSION_KEY);
  if (serialized) {
    try {
      return UserSession.deserialize(serialized);
    } catch {
      sessionStorage.removeItem(SESSION_KEY);
    }
  }
  return null;
}

function getTokenFromHash(): { token: string | null; expires: number | null } {
  const hash = window.location.hash.substring(1);
  const params = new URLSearchParams(hash);
  const token = params.get("access_token");
  const expiresIn = params.get("expires_in");
  return {
    token,
    expires: expiresIn ? Date.now() + parseInt(expiresIn, 10) * 1000 : null,
  };
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<UserSession | null>(restoreSession());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const { token, expires } = getTokenFromHash();
    if (token) {
      const s = new UserSession({
        clientId,
        redirectUri,
        token,
        tokenExpires: expires ? new Date(expires) : new Date(Date.now() + 1000 * 60 * 60 * 24 * 14),
        portal: "https://www.arcgis.com/sharing/rest",
      });
      setSession(s);
      saveSession(s);
      setLoading(false);
      window.history.replaceState({}, document.title, redirectUri);
      return;
    }
    setLoading(false);
  }, []);

  const signIn = () => {
    UserSession.beginOAuth2({ clientId, redirectUri, popup: false });
  };

  const signOut = () => {
    if (session) {
      setSession(null);
      sessionStorage.removeItem(SESSION_KEY);
    }
  };

  return (
    <AuthContext.Provider value={{ session, token: session?.token ?? null, signIn, signOut, loading }}>
      {children}
    </AuthContext.Provider>
  );
};