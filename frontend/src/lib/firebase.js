// src/lib/firebase.js
import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from 'firebase/auth'
import { getStorage, ref, uploadBytes, getDownloadURL, deleteObject, listAll } from 'firebase/storage'

// 🔧 REPLACE THESE with your Firebase project config
// Get from: Firebase Console → Project Settings → Your Apps → SDK setup
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const storage = getStorage(app)

const googleProvider = new GoogleAuthProvider()

// Auth helpers
export const signInWithGoogle = () => signInWithPopup(auth, googleProvider)
export const signInWithEmail = (email, password) => signInWithEmailAndPassword(auth, email, password)
export const registerWithEmail = (email, password) => createUserWithEmailAndPassword(auth, email, password)
export const logOut = () => signOut(auth)

// Storage helpers
export const uploadFile = async (file, userId) => {
  const timestamp = Date.now()
  const storageRef = ref(storage, `uploads/${userId}/${timestamp}_${file.name}`)
  await uploadBytes(storageRef, file)
  const url = await getDownloadURL(storageRef)
  return { url, path: storageRef.fullPath, name: `${timestamp}_${file.name}` }
}

export const getFileDownloadURL = (path) => {
  const fileRef = ref(storage, path)
  return getDownloadURL(fileRef)
}
