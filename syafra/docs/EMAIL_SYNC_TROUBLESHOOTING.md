# Email Visibility Issue - Complete Troubleshooting Guide

## Problem Summary

**Symptom:** Emails sent from SYAFRA (including password reset emails) are received on mobile but NOT visible on laptop web/desktop email client.

**This is NOT a Django/backend issue** - emails are being sent successfully. The issue is with email client synchronization or filtering.

## Immediate Actions to Try

### 1. Force Email Sync/Refresh

**Gmail Web:**
- Press `Ctrl + Shift + R` (hard refresh)
- Or `Ctrl + R` (normal refresh)
- Click "Refresh" button (circular arrow icon)

**Outlook Web:**
- Press `Ctrl + Shift + Delete` to clear cache, then refresh
- Click "Sync" button

### 2. Search for the Email

**Gmail Search Bar:**
```
subject:password OR from:syafra OR from:noreply
```

**Outlook Search:**
```
subject:password OR from:syafra
```

### 3. Check ALL These Folders

**Gmail:**
- [ ] Inbox
- [ ] Spam
- [ ] Junk
- [ ] Social
- [ ] Promotions
- [ ] Updates
- [ ] All Mail (archived emails)
- [ ] Trash

**Outlook:**
- [ ] Inbox
- [ ] Junk Email
- [ ] Clutter
- [ ] Archive
- [ ] Deleted Items

### 4. Clear Browser Cache & Try Incognito

**Chrome:**
1. `Ctrl + Shift + Delete`
2. Select "All time"
3. Check "Cached images and files"
4. Click "Clear data"
5. Open incognito: `Ctrl + Shift + N`
6. Go to Gmail and check

**Firefox:**
1. `Ctrl + Shift + Delete`
2. Select "Everything"
3. Click "Clear Now"
4. Open private window: `Ctrl + Shift + P`

**Edge:**
1. `Ctrl + Shift + Delete`
2. Select "All time"
3. Click "Clear now"
4. Open InPrivate: `Ctrl + Shift + N`

### 5. Try Different Browser

If Chrome doesn't work:
- Try Firefox
- Try Safari (Mac)
- Try Edge

### 6. Logout and Login Again

1. Click profile picture (top right)
2. Click "Sign out"
3. Clear all browser data
4. Sign back in
5. Check inbox

## Gmail-Specific Solutions

### Check Categories

1. Go to Gmail Settings ⚙️
2. Click **"See all settings"**
3. Go to **Inbox** tab
4. Check **Categories** section
5. Make sure "Primary" is checked
6. Save changes

### Check Filters

1. Gmail Settings ⚙️ → **Filters and Blocked Addresses**
2. Look for any filters that might:
   - Skip the inbox
   - Auto-archive
   - Auto-delete
   - Apply labels
3. Delete suspicious filters

### Check Spam Settings

1. Gmail Settings ⚙️ → **Spam**
2. Make sure spam filter is ON
3. Check "Never send to spam" exceptions (none should be needed)

### Disable Add-ons

1. Go to Gmail
2. Click puzzle icon (Get add-ons)
3. Click **Manage add-ons**
4. Temporarily disable all add-ons
5. Check if emails appear

## Outlook-Specific Solutions

### Repair Outlook Account

1. Close Outlook
2. Open Control Panel → Mail
3. Click "Email Accounts"
4. Select account → "Repair"
5. Restart Outlook

### Reset Outlook

1. File → Options → **Reset**
2. Close and reopen Outlook

### Check Exchange Settings

If using corporate email:
1. File → Account Settings
2. Check server settings
3. Ensure "Use Cached Exchange Mode" is checked

## Network/Firewall Solutions

### Try Different Network
- Switch from WiFi to mobile hotspot
- Try different WiFi network
- Check corporate firewall

### Disable VPN
- Temporarily disable VPN
- Check if emails appear
- Re-enable VPN if needed

### Check Proxy Settings
1. Internet Options → Connections → LAN Settings
2. Uncheck "Use a proxy server"
3. Try again

## What We Updated in Django

### Email Settings Updated

```python
# Added formatted sender name
DEFAULT_FROM_EMAIL = 'SYAFRA <syafra.official@gmail.com>'
SERVER_EMAIL = 'syafra.official@gmail.com'
```

This helps with:
- Email deliverability
- Email recognition in inbox
- Avoiding spam filters

## Diagnostic Questions

Please answer these to help identify the issue:

### Question 1: Which Device?
- [ ] Laptop web browser (which one?)
- [ ] Desktop email app (which one? Outlook, Thunderbird, etc.)
- [ ] Mobile (Gmail app, Outlook app, etc.)

### Question 2: Same Account?
- Are you checking the SAME email account on both devices?
  - Laptop: ___________
  - Mobile: ___________

### Question 3: What Happens When You Search?
- Try searching `from:syafra` in Gmail
- What results do you see?

### Question 4: Spam Checked?
- Have you checked Spam/Junk folder on laptop?
- Any filters configured?

## Quick Test

### Send Test Email to Yourself

```bash
python manage.py shell
```

Then:
```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'TEST EMAIL - Check All Folders',
    'This is a test email. Please check all folders including spam.',
    settings.DEFAULT_FROM_EMAIL,
    ['syafra.official@gmail.com'],
    fail_silently=False
)
print('Email sent! Check all folders.')
```

Then check on LAPTOP:
1. Inbox
2. Spam
3. All Mail
4. Try searching `TEST EMAIL`

## Most Likely Causes (Ranked by Probability)

1. **Email filtered to Spam/Junk** (Most likely)
   - Check spam folder
   - Mark as "Not Spam"

2. **Browser cache issue**
   - Clear cache
   - Try incognito mode
   - Try different browser

3. **Gmail Categories filtering**
   - Check Promotions, Social, Updates tabs
   - Move to Primary if found

4. **Email archived automatically**
   - Check "All Mail"
   - Gmail archives by default sometimes

5. **Network/sync delay**
   - Wait 5-10 minutes
   - Force sync

6. **Wrong email account**
   - Verify you're checking same account

7. **Corporate email policies**
   - Check with IT if using work email

## If Nothing Works

### Try These Extreme Measures

1. **Add to Contacts:**
   - Add `syafra.official@gmail.com` to contacts
   - Send yourself a test email
   - Check again

2. **Create Filter:**
   - Gmail → Settings → Filters → Create new filter
   - From: `syafra.official@gmail.com`
   - Never send to spam

3. **Check with IT:**
   - If using corporate email
   - Check email retention policies
   - Check email gateway settings

4. **Use Different Email:**
   - Try registering with a different email
   - Test password reset with that email
   - See if it's account-specific

## Summary

**Django Backend:** ✅ Working correctly
**Email Sending:** ✅ Verified working
**Email Template:** ✅ Fixed
**Email Settings:** ✅ Updated with formatted sender

**Issue Location:** Email client on laptop

**Recommended Actions:**
1. Check Spam/Junk folder
2. Search for "from:syafra"
3. Clear browser cache
4. Try incognito mode
5. Check all Gmail tabs

---

**Still having issues?** Let me know:
- Which email client you're using on laptop
- What happens when you search `from:syafra`
- Whether you checked the Spam folder
