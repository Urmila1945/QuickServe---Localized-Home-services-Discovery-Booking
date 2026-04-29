# QuickServe - How to Start

## Step 1: First Time Setup
```
Double-click: FIX.bat
```
This installs everything you need.

## Step 2: Start the App
```
Double-click: START.bat
```
Wait 10 seconds for servers to start.

## Step 3: Login
Browser opens to: http://localhost:5173

**Login with:**
- Email: `admin@quickserve.com`
- Password: `admin123`

## Step 4: Stop the App
```
Double-click: STOP.bat
```

---

## Getting "Network Error"?

**The backend is not running!**

**Fix:**
1. Close browser
2. Run `START.bat` again
3. Wait 10-15 seconds
4. Refresh browser

**Still not working?**
1. Run `STOP.bat`
2. Run `START_MONGODB.bat`
3. Run `START.bat`
4. Wait 15 seconds

---

## Files You Need

- `FIX.bat` - Setup (run once)
- `START.bat` - Start app (run every time)
- `STOP.bat` - Stop app
- `START_MONGODB.bat` - Start MongoDB only

---

**That's it!** 🎉
