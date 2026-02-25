# Verbatim Extractor

A web app for policy debaters to extract highlighted and underlined text from Verbatim-formatted Word documents. Preserves full card structure (tags & cites) while stripping un-marked body text.

---

## Project Structure

```
verbatim-app/
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── components/     # AuthPage, Dashboard, LoadingScreen
│   │   ├── hooks/          # useAuth
│   │   ├── lib/            # firebase.js
│   │   └── App.jsx
│   └── package.json
├── api/
│   ├── index.py            # FastAPI backend (Vercel serverless)
│   └── requirements.txt
├── scripts/
│   └── cleanup-function/   # Firebase Cloud Function (daily cleanup)
│       ├── index.js
│       └── package.json
├── vercel.json             # Vercel deployment config
└── .env.example            # Environment variable template
```

---

## Setup Guide

### Step 1 — Firebase Project

1. Go to [https://console.firebase.google.com](https://console.firebase.google.com)
2. Create a new project (or use existing)
3. Enable **Authentication**:
   - Go to Authentication → Sign-in method
   - Enable **Email/Password**
   - Enable **Google**
4. Enable **Storage**:
   - Go to Storage → Get started
   - Choose a region
   - Start in **production mode**
5. Set Storage Rules (allow authenticated users only):

```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /uploads/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    match /outputs/{userId}/{allPaths=**} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if false; // Only backend writes
    }
  }
}
```

6. Get your **Web App config**:
   - Project Settings → Your apps → Add app → Web
   - Copy the `firebaseConfig` object values

7. Get your **Service Account** (for backend):
   - Project Settings → Service accounts → Generate new private key
   - Download the JSON file — you'll paste its contents as an env var

---

### Step 2 — Deploy to Vercel

1. Push this project to GitHub
2. Go to [https://vercel.com](https://vercel.com) → New Project → Import your repo
3. Set the **Root Directory** to the repo root
4. Add these **Environment Variables** in Vercel project settings:

| Variable | Value | Where |
|---|---|---|
| `VITE_FIREBASE_API_KEY` | From Firebase web app config | Frontend |
| `VITE_FIREBASE_AUTH_DOMAIN` | e.g. `your-project.firebaseapp.com` | Frontend |
| `VITE_FIREBASE_PROJECT_ID` | Your project ID | Frontend |
| `VITE_FIREBASE_STORAGE_BUCKET` | e.g. `your-project.appspot.com` | Frontend |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | From Firebase config | Frontend |
| `VITE_FIREBASE_APP_ID` | From Firebase config | Frontend |
| `FIREBASE_SERVICE_ACCOUNT` | Entire service account JSON as string | Backend |

5. Deploy!

---

### Step 3 — Daily Cleanup Function (Firebase)

This deletes all uploaded files from Firebase Storage every night at midnight UTC.

```bash
# Install Firebase CLI if you haven't
npm install -g firebase-tools

# Login
firebase login

# Navigate to the function directory
cd scripts/cleanup-function
npm install

# Initialize Firebase in this folder (select your project)
firebase init functions

# Deploy the function
firebase deploy --only functions
```

You can verify it's running in **Firebase Console → Functions → Logs**.

---

## Local Development

```bash
# Frontend
cd frontend
cp ../.env.example .env.local
# Fill in your Firebase values in .env.local
npm install
npm run dev
```

```bash
# Backend (separate terminal)
cd api
pip install -r requirements.txt
# Set environment variables
export FIREBASE_SERVICE_ACCOUNT='{"type":"service_account",...}'
export VITE_FIREBASE_STORAGE_BUCKET='your-project.appspot.com'
uvicorn index:app --reload --port 8000
```

---

## Extraction Modes

| Mode | Behavior |
|---|---|
| **Highlighted OR Underlined** (default) | Keeps any run that is highlighted or underlined |
| **Highlighted Only** | Keeps only runs with a highlight color |
| **Underlined Only** | Keeps only underlined runs |

**Structure detection**: Paragraphs where all non-empty runs are bold are treated as tags/cites and always preserved in full.

---

## Storage Policy

- Uploaded files are **deleted immediately** after processing on the backend
- Processed output files are stored temporarily with a **1-hour signed download URL**
- A Firebase Cloud Function clears **all remaining files** every day at **12:00 AM UTC**
- No document content is ever logged or retained beyond these windows
