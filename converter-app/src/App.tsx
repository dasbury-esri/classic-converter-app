import './App.css'
import Converter from './components/Converter'
import { useAuth } from './auth/useAuth'

function App() {
  const { token, signIn, signOut, loading, userInfo } = useAuth();

  return (
    <div className="App">
      <div style={{ marginBottom: 24 }}>
        {!token ? (
          <button
            onClick={signIn}
            disabled={loading}
            style={{
              opacity: loading ? 0.5 : 1,
              cursor: loading ? "not-allowed" : "pointer",
              padding: "10px 24px",
              fontSize: "16px",
              fontWeight: "bold",
              background: "#0079c1",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
            }}
          >
            {loading ? "Signing in..." : "Sign In to ArcGIS"}
          </button>
        ) : (
          <button
            onClick={signOut}
            style={{
              opacity: 1,
              cursor: "pointer",
              padding: "10px 24px",
              fontSize: "16px",
              fontWeight: "bold",
              background: "#ccc",
              color: "#333",
              border: "none",
              borderRadius: "4px",
            }}
          >
            Sign Out of ArcGIS
          </button>
        )}
      </div>
      {userInfo && (
        <div style={{ margin: "10px 0", fontSize: "14px", color: "#0079c1" }}>
          You are signed in as: "<strong>{userInfo.username}</strong>" (User Role: <strong>{userInfo.role}</strong> / User Type: <strong>{userInfo.userType}</strong>)
        </div>
      )}
      <Converter />
    </div>
  );
}

export default App
