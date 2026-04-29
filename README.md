# QuickServe - Quick Start

## 🚀 First Time Setup

1. **Run:** `FIX.bat`
   - Installs all dependencies
   - Starts MongoDB
   - Creates admin user

## ▶️ Start Application

2. **Run:** `START.bat`
   - Starts backend (port 8000)
   - Starts frontend (port 5173)
   - Opens browser automatically
   - **Wait 10 seconds** before logging in

## 🔐 Login

**Admin:**
- Email: `admin@quickserve.com`
- Password: `admin123`

**Demo Customer:**
- Email: `customer@demo.com`
- Password: `password123`

**Demo Provider:**
- Email: `provider@demo.com`
- Password: `password123`

## ⛔ Stop Application

3. **Run:** `STOP.bat`

---

## 🔧 Troubleshooting

### Network Error / Connection Refused?

**Backend is not running!**

**Fix:**
1. Run `FIX.bat`
2. Run `START.bat`
3. **Wait 10-15 seconds**
4. Refresh browser

### MongoDB Error?

**Fix:**
```bash
START_MONGODB.bat
```

Or manually (as Administrator):
```bash
net start MongoDB
```

### Port Already in Use?

**Fix:**
```bash
STOP.bat
```

---

## 🌐 URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📝 Manual Start (Advanced)

**Backend:**
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## ✅ Requirements

- Python 3.8+
- Node.js 16+
- MongoDB 4.4+
