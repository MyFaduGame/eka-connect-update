// firebase-messaging-sw.js

// Import Firebase scripts
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// Firebase config
firebase.initializeApp({
  apiKey: "AIzaSyDg8duL9BlbaZmK31mBNNLVBSf8Ld9y2zg",
  authDomain: "eka-connect-update.firebaseapp.com",
  projectId: "eka-connect-update",
  storageBucket: "eka-connect-update.appspot.com",
  messagingSenderId: "439435270320",
  appId: "1:439435270320:web:eaa251d003f08a6f56c375",
  measurementId: "G-RMSBFJHTJ5"
});

// Initialize messaging
const messaging = firebase.messaging();

// Optional: Background notification handler
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});
