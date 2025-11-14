import React, { useEffect, useState } from "react";
import { UserSession } from "@esri/arcgis-rest-auth";
import { clientId, redirectUri, SESSION_KEY, saveSession, restoreSession, getTokenFromHash } from "./AuthUtils";
import { AuthContext } from "./AuthContext";

const authMethod = import.meta.env.VITE_AUTH_METHOD;
const clientId = import.meta.env.VITE_CLIENT_ID;
const redirectUri = import.meta.env.VITE_REDIRECT_URI;

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
    // Use different OAuth2 methods for dev and prod
    if (authMethod === "dev") {
      UserSession.beginOAuth2({
        clientId,
        redirectUri,
        popup: false // Use popup for dev
      });
    } else {
      UserSession.beginOAuth2({
        clientId,
        redirectUri,
        popup: false // Use redirect for prod
      });
    }
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