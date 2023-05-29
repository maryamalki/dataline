import { createContext, useContext, useEffect, useState } from "react";
import { IConnection } from "../Conversation/types";
import { api } from "../api";

type ConnectionListContextType = [
  IConnection[] | null,
  (connections: IConnection[]) => void
];

const ConnectionListContext = createContext<ConnectionListContextType>([
  null,
  () => {},
]);

export const useConnectionList = () => {
  const context = useContext(ConnectionListContext);
  if (context === undefined) {
    throw new Error("useConnection must be used within a ConnectionProvider");
  }
  return context;
};

export const ConnectionListProvider = ({
  children,
}: React.PropsWithChildren) => {
  const [connections, setConnections] = useState<IConnection[]>([]);

  useEffect(() => {
    // replace this with your actual API call
    api.listConnections().then((response) => {
      if (response.status === "ok") {
        setConnections(response.sessions);
      } else {
        alert("Error loading connections");
      }
    });
  }, []);

  return (
    <ConnectionListContext.Provider value={[connections, setConnections]}>
      {children}
    </ConnectionListContext.Provider>
  );
};
