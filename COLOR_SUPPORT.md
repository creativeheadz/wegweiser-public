# Color Support in Installation Scripts

## Issue

If you see raw escape codes like `\033[1mDevelopment\033[0m` instead of colored text, your terminal isn't interpreting ANSI color codes correctly.

## Quick Fix

### Option 1: Set TERM Variable (Recommended)

Before running any installation script:

```bash
export TERM=xterm-256color
```

Then run the script:

```bash
sudo bash install.sh
```

### Option 2: Add to Your Shell Configuration

Make it permanent by adding to your `~/.bashrc`:

```bash
echo 'export TERM=xterm-256color' >> ~/.bashrc
source ~/.bashrc
```

### Option 3: Test Color Support

Run the color test script:

```bash
bash test-colors.sh
```

If you see actual colors (not escape codes), your terminal is configured correctly!

## Why This Happens

### WSL/Windows Terminal
- **Problem:** Default WSL installations may not have TERM set correctly
- **Solution:** Set `TERM=xterm-256color` as shown above

### Legacy Terminals
- **Problem:** Old terminal emulators may not support ANSI colors
- **Solution:** Use a modern terminal like:
  - Windows Terminal (recommended for WSL)
  - iTerm2 (macOS)
  - GNOME Terminal (Linux)
  - Konsole (Linux)

## Verification

After applying the fix, you should see:

**Before (broken):**
```
1) \033[1mDevelopment\033[0m
```

**After (working):**
```
1) Development  (in bold)
```

## If Colors Still Don't Work

### Check Your Terminal
```bash
echo $TERM
```

Should output: `xterm-256color` or similar

### Test Basic Colors
```bash
echo -e "\033[0;31mRED\033[0m"
```

Should show RED in red color.

### Force Color in Scripts

If nothing else works, you can disable colors by commenting out color variables:

Edit the script and change:
```bash
# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
# ... etc
```

To:
```bash
# Text formatting (disabled)
RED=''
GREEN=''
# ... etc
```

This makes scripts work without colors (plain text only).

## Recommended Setup for WSL Users

1. **Install Windows Terminal** (from Microsoft Store)
   - Better color support than legacy cmd/PowerShell
   - Native WSL integration

2. **Configure WSL in Windows Terminal:**
   - Open Windows Terminal
   - Settings → Ubuntu/WSL profile
   - Appearance → Color scheme: "One Half Dark" or "Campbell"

3. **Set TERM in WSL:**
   ```bash
   echo 'export TERM=xterm-256color' >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Test:**
   ```bash
   bash test-colors.sh
   ```

## All Installation Scripts Updated

The following scripts have been updated with automatic TERM setting:

- ✅ `install.sh`
- ✅ `install-enhanced.sh`
- ✅ `check-prereqs.sh`
- ✅ `configure-env.sh`
- ✅ `verify-setup-enhanced.sh`

They will now automatically try to enable color support when run.

## Colors Used

| Color | Purpose | Example |
|-------|---------|---------|
| **GREEN** | Success messages | [✓] Installation complete |
| **RED** | Errors | [✗] Database connection failed |
| **YELLOW** | Warnings | [!] Low disk space |
| **BLUE** | Info messages | [i] Starting installation... |
| **CYAN** | Headers/sections | === Step 1: Configuration === |
| **MAGENTA** | Banners | Wegweiser Installation Wizard |
| **BOLD** | Emphasis | **Development** mode |

## Support

If colors still don't work after trying these steps, the scripts will still function correctly - they'll just show escape codes instead of colors. The functionality is not affected.

For further help, see:
- https://en.wikipedia.org/wiki/ANSI_escape_code
- https://docs.microsoft.com/en-us/windows/terminal/
