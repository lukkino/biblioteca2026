import { createContext, useContext } from "react"

// { user: {name, email, created_at, last_seen_version} | null, logout, markVersionSeen }
export const AuthContext = createContext({ user: null, logout: async () => {}, markVersionSeen: async () => {} })
export const useAuth = () => useContext(AuthContext)
