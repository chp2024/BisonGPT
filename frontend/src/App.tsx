// App.tsx
import { useEffect, useState } from "react";
import { sessionState, useChatSession } from "@chainlit/react-client";
import { Playground } from "./components/playground";
import { Login } from "./components/login"; // Import Login component
import { useRecoilValue } from "recoil";
import "./index.css";

const userEnv = {};

function App() {
  const { connect } = useChatSession();
  const session = useRecoilValue(sessionState);
  const [isAuthenticated, setIsAuthenticated] = useState(false); // Track authentication state

  // Function to handle successful login
  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  useEffect(() => {
    if (session?.socket.connected) {
      return;
    }
    fetch("http://localhost:80/custom-auth")
      .then((res) => res.json())
      .then((data) => {
        connect({
          userEnv,
          accessToken: `Bearer: ${data.token}`,
        });
      });
  }, [connect]);

  return (
    <div>
      {/* Conditionally render based on authentication status */}
      {isAuthenticated ? <Playground /> : <Login onLogin={handleLogin} />}
    </div>
  );
}

export default App;
