# Safari Login Issues - Fix Documentation

## Problem Description
Users experiencing login issues on Safari (MacBook) with:
1. Erratic preloader animation behavior
2. Persistent "reCAPTCHA error" preventing login
3. Issue specific to Safari - works fine on other browsers/devices

## Root Causes Identified

### 1. Pace.js Animation Issues
- Safari's WebKit rendering engine handles CSS transforms differently
- Animation timing conflicts with reCAPTCHA loading
- Missing Safari-specific CSS optimizations (`will-change`, `-webkit-backface-visibility`)

### 2. reCAPTCHA v3 Loading Race Condition
- reCAPTCHA script loading asynchronously without proper ready-state checks
- Pace.js AJAX tracking interfering with reCAPTCHA network requests
- Missing error handling for token generation failures
- Form submission occurring before reCAPTCHA token is ready

### 3. Event Lag Tracking
- Pace.js event lag monitoring causing performance issues on Safari
- Excessive animation recalculations

## Fixes Implemented

### 1. Enhanced reCAPTCHA Loading
**File: `app/templates/login/index.html`**

- Added `async defer` attributes to reCAPTCHA script tag
- Implemented robust initialization with retry logic
- Added state tracking (`recaptchaLoaded`, `recaptchaToken`)
- 300ms delay after page load to let Pace.js settle
- Comprehensive error handling and logging

### 2. Form Validation
**File: `app/templates/login/index.html`**

- Added `validateLoginForm()` function to check token before submission
- Fallback mechanism to generate token on-demand if missing
- Clear user-friendly error messages
- Prevents form submission if reCAPTCHA not ready

### 3. Safari-Optimized Pace.js Configuration
**File: `app/templates/login/index.html`**

```javascript
window.paceOptions = {
    elements: false,           // Disable element tracking
    restartOnRequestAfter: false,
    ghostTime: 50,            // Reduced from default
    minTime: 100,             // Reduced from default
    catchupTime: 50,
    initialRate: 0.1,
    eventLag: false,          // Disable event lag tracking
    ajax: false               // Disable AJAX tracking (prevents reCAPTCHA interference)
};
```

### 4. Safari-Compatible CSS
**File: `app/static/css/pace.minimal.safari-fix.css`**

Added Safari-specific optimizations:
- `will-change: transform` for GPU acceleration hints
- `-webkit-backface-visibility: hidden` to prevent flickering
- `transform: translateZ(0)` to force hardware acceleration
- `-webkit-font-smoothing: antialiased` for smoother rendering
- Explicit `-webkit-` prefixed animations
- Safari-specific animation duration adjustments

### 5. Enhanced Server-Side Validation
**File: `app/routes/login/login.py`**

Improved `verify_recaptcha_v3()` function:
- Better error handling with specific error codes
- Timeout handling (5 second limit)
- Safari detection via User-Agent
- More detailed logging for debugging
- User-friendly error messages based on error type:
  - `timeout-or-duplicate`: "Please refresh the page"
  - `missing-input-response`: "Please wait a moment"
  - Low score on Safari: Specific guidance to refresh

## Testing Checklist

### Safari-Specific Tests
- [ ] Test on Safari 17+ (latest version)
- [ ] Test on older Safari versions (16.x)
- [ ] Test with Safari Developer Tools open
- [ ] Test with "Prevent Cross-Site Tracking" enabled/disabled
- [ ] Test with "Block all cookies" setting
- [ ] Clear Safari cache and cookies before testing

### Functional Tests
- [ ] Preloader animation is smooth (not erratic)
- [ ] reCAPTCHA token loads successfully
- [ ] Login succeeds with valid credentials
- [ ] Appropriate error messages appear for failures
- [ ] Console logs show successful token generation
- [ ] No JavaScript errors in Safari console

### Browser Console Checks
Look for these log messages in Safari Developer Console:
```
✓ "Safari detected, using optimized Pace.js settings"
✓ "reCAPTCHA token loaded successfully"
✗ "reCAPTCHA not ready, retrying..."
✗ "reCAPTCHA execution error: ..."
```

## Troubleshooting Guide

### If preloader still behaves erratically:
1. Check Safari version (update if < 16.0)
2. Disable Safari extensions temporarily
3. Check if GPU acceleration is enabled in Safari preferences
4. Try clearing "Website Data" in Safari Settings

### If reCAPTCHA still fails:
1. Check browser console for specific error messages
2. Verify reCAPTCHA public key is correct in configuration
3. Check if Safari is blocking third-party scripts
4. Disable "Prevent Cross-Site Tracking" in Safari Privacy settings
5. Add `www.google.com` and `www.gstatic.com` to allowed sites

### If form submission fails silently:
1. Open Safari Developer Tools → Console
2. Look for JavaScript errors
3. Check Network tab for failed reCAPTCHA requests
4. Verify the `g-recaptcha-response` field has a value before submit

## Safari Privacy Settings Impact

### Settings that may cause issues:
1. **Prevent Cross-Site Tracking**: May block reCAPTCHA (suggest disabling for this site)
2. **Block all cookies**: Will prevent login entirely
3. **Fraudulent website warning**: May interfere with reCAPTCHA
4. **Content Blockers**: May block Google reCAPTCHA resources

### Recommended Safari Settings for This Site:
1. Settings → Safari → Privacy → Website Settings → [yoursite.com]
2. Allow cookies: Yes
3. Prevent Cross-Site Tracking: Off (for this site)
4. Content Blockers: Disabled

## Monitoring & Logging

Server-side logs now include:
- Safari detection: `Safari: True/False`
- reCAPTCHA error codes: `error-codes=['...']`
- Token generation success/failure
- User agent string for debugging

Check logs at: `/opt/wegweiser/wlog/wegweiser.log`

Look for entries like:
```
reCAPTCHA result: success=False, score=0.0, errors=['timeout-or-duplicate'], IP: x.x.x.x, Safari: True
```

## Additional Recommendations

### For Users:
1. **Update Safari**: Ensure using Safari 16.0 or later
2. **Clear Cache**: Safari → Preferences → Privacy → Manage Website Data → Remove All
3. **Disable Extensions**: Temporarily disable all Safari extensions
4. **Try Private Window**: Test login in a new Private Window
5. **Check Privacy Settings**: Adjust privacy settings as noted above

### For Developers:
1. Monitor server logs for Safari-specific patterns
2. Consider A/B testing with/without Pace.js on Safari
3. Add client-side error reporting (e.g., Sentry)
4. Create Safari-specific test cases in CI/CD

## Rollback Plan

If issues persist, you can rollback changes:

1. Revert template changes:
   ```bash
   git checkout HEAD -- app/templates/login/index.html
   ```

2. Restore old CSS:
   ```bash
   git checkout HEAD -- app/static/css/pace.minimal.css
   ```

3. Revert login.py changes:
   ```bash
   git checkout HEAD -- app/routes/login/login.py
   ```

## Future Improvements

1. **Consider reCAPTCHA v2 fallback** for Safari users who continue to have issues
2. **Add Safari version detection** to apply fixes only for problematic versions
3. **Implement feature detection** instead of browser detection where possible
4. **Add telemetry** to track reCAPTCHA success rates by browser
5. **Consider alternatives to Pace.js** (e.g., NProgress, Nprogress, or custom solution)

## Support

If Safari users continue experiencing issues:
1. Collect Safari version, macOS version, and full error messages
2. Check browser console for JavaScript errors
3. Test with all Safari extensions disabled
4. Test in Safari Private Browsing mode
5. Contact support with log entries from `/opt/wegweiser/wlog/wegweiser.log`
