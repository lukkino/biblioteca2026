import { createContext, useContext } from "react"

// { user: {name, email} | null, logout: () => Promise }
export const AuthContext = createContext({ user: null, logout: async () => {} })
export const useAuth = () => useContext(AuthContext)
