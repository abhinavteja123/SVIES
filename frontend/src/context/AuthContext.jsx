import { createContext, useContext, useState, useEffect } from 'react';
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth';
import { auth } from '../config/firebase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const token = await firebaseUser.getIdTokenResult(true);
          const userRole = token.claims.role;

          // ── Government portal: only admin-registered users with an explicit
          //    role claim are allowed in. If there's no role claim at all,
          //    the account was never registered by an admin → sign out.
          if (!userRole) {
            await signOut(auth);
            setUser(null);
            setRole(null);
            setLoading(false);
            return;
          }

          setUser(firebaseUser);
          setRole(userRole);
        } catch {
          // Token retrieval failed → sign out to be safe
          await signOut(auth);
          setUser(null);
          setRole(null);
        }
      } else {
        setUser(null);
        setRole(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const login = async (email, password) => {
    return signInWithEmailAndPassword(auth, email, password);
  };

  const logout = async () => {
    return signOut(auth);
  };

  const getToken = async () => {
    if (!user) return null;
    return user.getIdToken();
  };

  const refreshRole = async () => {
    if (!user) return;
    try {
      const token = await user.getIdTokenResult(true);
      setRole(token.claims.role || null);
    } catch {
      await signOut(auth);
      setUser(null);
      setRole(null);
    }
  };

  const value = { user, role, loading, login, logout, getToken, refreshRole };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
