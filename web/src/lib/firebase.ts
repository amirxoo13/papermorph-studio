"use client";

// Identity Platform / Firebase Auth on the browser side.
//
// The API now verifies a real ID token (services/api/src/auth.py), so the only
// way to call it is to sign in and send the token. Nothing here may invent an
// identity: there is no header to set and no uid to pass.
//
// The values below are public client configuration, not secrets, but they are
// still read from the environment so the same build can point at another
// project. apphosting.yaml supplies them.

import { initializeApp, getApp, getApps, FirebaseApp } from "firebase/app";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as fbSignOut,
  Auth,
  User,
} from "firebase/auth";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    // Failing here is better than rendering a signed-out page that looks broken
    // for no stated reason.
    throw new Error(
      `${name} is not set. Add it to web/apphosting.yaml so the browser can reach Identity Platform.`,
    );
  }
  return value;
}

export function firebaseApp(): FirebaseApp {
  if (getApps().length) return getApp();
  return initializeApp({
    apiKey: requiredEnv("NEXT_PUBLIC_FIREBASE_API_KEY"),
    authDomain: requiredEnv("NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN"),
    projectId: requiredEnv("NEXT_PUBLIC_GOOGLE_CLOUD_PROJECT"),
  });
}

export function firebaseAuth(): Auth {
  return getAuth(firebaseApp());
}

export function watchUser(cb: (user: User | null) => void): () => void {
  return onAuthStateChanged(firebaseAuth(), cb);
}

export async function signIn(email: string, password: string): Promise<User> {
  const cred = await signInWithEmailAndPassword(firebaseAuth(), email, password);
  return cred.user;
}

export async function signUp(email: string, password: string): Promise<User> {
  const cred = await createUserWithEmailAndPassword(firebaseAuth(), email, password);
  return cred.user;
}

export async function signOut(): Promise<void> {
  await fbSignOut(firebaseAuth());
}

/** The current user's ID token, or null when nobody is signed in. */
export async function idToken(): Promise<string | null> {
  const user = firebaseAuth().currentUser;
  if (!user) return null;
  return user.getIdToken();
}
