# Firebase Setup Guide

## 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Enable Firestore Database
4. Enable Authentication (optional)

## 2. Get Service Account Key

1. Go to Project Settings > Service Accounts
2. Click "Generate new private key"
3. Download the JSON file
4. Replace `config/firebase-credentials.json` with your downloaded file

## 3. Update Environment Variables

Update your `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key_here
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com/
JWT_SECRET=your-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 4. Firestore Collections

The application will automatically create these collections:
- `users` - User authentication and profiles
- `facilities` - Healthcare facilities
- `conversations` - Chat conversations
- `notifications` - User notifications
- `sehat_card_applications` - Sehat card applications
- `agent_decisions` - AI agent decision logs
- `follow_ups` - Follow-up messages

## 5. Security Rules (Optional)

Add these Firestore security rules:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## 6. Run the Application

```bash
./run.sh
```

The application will automatically seed sample data on first run.
