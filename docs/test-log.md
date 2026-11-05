# Test log — UI polish pass

**Branch:** `feature/ui-polish` · **Date:** 2026-11-05 · **Tested by:** Claude Code (automated browser runs) for Siddu H Gadad

Every ✅ below comes from a check that was actually run in a real browser. The number next to it is how many
separate checks were run for that cell. "—" means the feature does not apply to that role (for example, a viewer cannot
log progress, and an admin can edit every project, so there is no "someone else's project" case). It never means "passed".

## How it was tested

- **Browser:** Microsoft Edge (Chromium), headless, driven by `playwright-core`. Playwright was installed in a
  temporary folder outside the repo, so it is **not** a project dependency, and the scripts are not committed.
- **Widths:** desktop = 1280px, mobile = 375px (the full interactive flows ran at both); tablet = 768px (layout audit only).
- **Data:** a separate scratch database (`vanatrack_seed_scratch`) loaded with `python -m scripts.seed --reset`, served by
  a separate API (port 8010) and Vite server (port 5180). The normal `vanatrack` database was not touched; its row counts
  were the same before and after the run.
- **Roles:** `admin@`, `manager@`, `manager2@`, `viewer@vanatrack.demo` (password in the README), plus logged-out visitors.
- **Totals:** 212 interactive checks (0 failed) · 254 loading/empty/error checks (0 failed) ·
  132 page × role × width layout audits.

What each automated check looks at:

| Suite | What it does |
|---|---|
| Layout audit | Opens every page as every role at 375 / 768 / 1280 and measures: horizontal scroll (`scrollWidth > clientWidth`), every link/button/input/switch at least 40×40px, inputs without a label, icon buttons without a name, text contrast below 4.5:1 (3:1 for large text), console errors, and `document.title`. Screenshots were saved and reviewed by eye. |
| Interactive flows | Logs in through the form and works through each feature as that role: validation messages, success and error toasts, confirm dialogs (and Escape cancelling them), Tab staying inside dialogs and the mobile menu, the 600 → 850 scenario, hidden actions, the 403s from the API, and logout. |
| States | Holds back, empties or fails (HTTP 500) one API call at a time in the browser, and checks that the view shows a loading placeholder, an empty message, or an error with "Try again". No data is changed. |

## Feature × device × role

| Feature | Desktop admin | Desktop manager | Desktop manager2 | Desktop viewer | Mobile admin | Mobile manager | Mobile manager2 | Mobile viewer |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Layout: no horizontal scroll (every page) | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 |
| Layout: tap targets ≥ 40px (every page) | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 |
| A11y: inputs labelled, icon buttons named, contrast ≥ 4.5:1 | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 |
| Page title set per route | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 | ✅ 9 | ✅ 11 | ✅ 11 | ✅ 9 |
| Login | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Create project | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 3 | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 3 |
| Dialogs | ✅ 1 | ✅ 1 | ✅ 1 | — | ✅ 1 | ✅ 1 | ✅ 1 | — |
| Progress scenario | ✅ 7 | ✅ 7 | ✅ 7 | — | ✅ 7 | ✅ 7 | ✅ 7 | — |
| Dashboard | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Edit project | ✅ 1 | ✅ 1 | ✅ 1 | — | ✅ 1 | ✅ 1 | ✅ 1 | — |
| Undo progress | ✅ 2 | ✅ 1 | ✅ 1 | — | ✅ 2 | ✅ 1 | ✅ 1 | — |
| Delete project | ✅ 2 | ✅ 2 | ✅ 2 | — | ✅ 2 | ✅ 2 | ✅ 2 | — |
| User management | ✅ 4 | — | — | — | ✅ 4 | — | — | — |
| Toasts | ✅ 2 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 2 | ✅ 1 | ✅ 1 | ✅ 1 |
| Export CSV | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Activity | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Not found / status | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Users page access | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Layout / navigation | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 2 |
| Logout | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Console | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 | ✅ 1 |
| Permissions | — | ✅ 3 | ✅ 3 | ✅ 3 | — | ✅ 3 | ✅ 3 | ✅ 3 |
| Loading / empty / error states (12 views) | ✅ 34 | ✅ 31 | ✅ 31 | ✅ 31 | ✅ 34 | ✅ 31 | ✅ 31 | ✅ 31 |

### Logged-out pages

| Logged-out check | Desktop | Mobile |
|---|:-:|:-:|
| wrong password shows a clear error | ✅ 1 | ✅ 1 |
| mismatched passwords rejected inline | ✅ 1 | ✅ 1 |
| valid registration -> welcome toast, logged in as viewer | ✅ 1 | ✅ 1 |
| /status page reports API and database connected | ✅ 1 | ✅ 1 |
| Layout of /login (no h-scroll, targets ≥ 40px) at 375 / 768 / 1280 | ✅ 2 | ✅ 1 |
| Layout of /register (no h-scroll, targets ≥ 40px) at 375 / 768 / 1280 | ✅ 2 | ✅ 1 |
| Layout of /status (no h-scroll, targets ≥ 40px) at 375 / 768 / 1280 | ✅ 2 | ✅ 1 |
| Layout of /does-not-exist (no h-scroll, targets ≥ 40px) at 375 / 768 / 1280 | ✅ 2 | ✅ 1 |

### Tablet (768px) layout audit

| Role | Pages checked at 768px | Horizontal scroll | Tap targets < 40px | Unlabelled / contrast issues |
|---|:-:|:-:|:-:|:-:|
| anonymous | 4 | 0 | 0 | 0 |
| admin | 9 | 0 | 0 | 0 |
| manager | 11 | 0 | 0 | 0 |
| manager2 | 11 | 0 | 0 | 0 |
| viewer | 9 | 0 | 0 | 0 |

### Loading / empty / error states, per view (all roles and both devices combined)

| View | Loading | Empty | Error |
|---|:-:|:-:|:-:|
| Projects list | ✅ 8 | ✅ 8 | ✅ 8 |
| Project detail | ✅ 8 | — | ✅ 8 |
| Progress history + chart | ✅ 8 | ✅ 8 | ✅ 8 |
| Project activity panel | ✅ 8 | ✅ 8 | ✅ 8 |
| Activity page | ✅ 8 | ✅ 8 | ✅ 8 |
| Dashboard KPIs | ✅ 8 | — | ✅ 8 |
| Dashboard progress-by-project | ✅ 8 | ✅ 8 | ✅ 8 |
| Dashboard trend chart | ✅ 8 | ✅ 8 | ✅ 8 |
| Dashboard by type | ✅ 8 | ✅ 8 | ✅ 8 |
| Dashboard by state | ✅ 8 | ✅ 8 | ✅ 8 |
| Dashboard attention list | ✅ 8 | ✅ 8 | ✅ 8 |
| Users (admin) | ✅ 2 | ✅ 2 | ✅ 2 |

"—" under Empty: that view has no empty case (a single project or the KPI totals are always present).

## The required scenario (target 1,000, 600 → 850)

Run as admin, manager and manager2, at 1280px and at 375px. Each run created a new project with a target of 1,000 trees, then:
- `-5` and `abc` were rejected with "Enter a whole number, like 850 (no commas, decimals or minus sign)."
- 600 was saved (toast "Progress saved: 0 → 600 trees."), then 850 (toast "600 → 850"); the page showed **85%**.
- The history showed "600 → 850" with the author's name and the time.
- Going down to 700 with no reason was refused: "The total is going down. Tick this box and explain why."
- The project list (reached by clicking in the app, no page reload) showed 85%, and the dashboard figures changed.
- manager / manager2 on the other manager's project: Edit, Delete and Log progress were hidden, the edit URL showed
  "Not authorized", and the API answered **403 "You can only modify projects you own."**
- Viewer: the API answered 403 "Your role (viewer) cannot perform this action." when creating, and 403 when editing or logging progress.

## Not tested, or only partly tested

- **Real phones and touch input.** Mobile means a 375px-wide window in desktop Edge; touch gestures and on-screen keyboards were not used.
- **Firefox and Safari.** Only Chromium (Edge) was used.
- **Screen readers.** Not tried with NVDA, JAWS or VoiceOver. Only the ARIA attributes, labels, focus order and live regions were checked automatically.
- **768px interactive flows.** Tablet width had the layout audit only, not the click-through flows.
- **The deployed site.** Everything ran locally. The live Vercel / Render / Neon deployment was not tested in this pass.
- **Session expiry** (a 401 logging the user out automatically) was not re-tested in this pass.
- **Contrast** was measured on solid backgrounds only. Placeholder text and text inside charts (SVG) were not included.
- **Loading checks** confirm that a loading placeholder is on screen while the request is held back. They do not check which placeholder it is.
- The browser's own "Failed to load resource: 404" console line on `/projects/999999` is expected (the API correctly answers 404), and it is not counted as an app error.

## Every interactive check

<details>
<summary>212 checks (click to expand)</summary>

| Role | Device | Feature | Check | Result | Detail |
|---|---|---|---|---|---|
| anonymous | desktop | Login | wrong password shows a clear error | ✅ | Incorrect email or password. |
| anonymous | desktop | Register | mismatched passwords rejected inline | ✅ |  |
| anonymous | desktop | Register | valid registration -> welcome toast, logged in as viewer | ✅ |  |
| anonymous | desktop | Not found / status | /status page reports API and database connected | ✅ |  |
| admin | desktop | Login | valid login lands on the dashboard | ✅ |  |
| admin | desktop | Create project | empty form is rejected with inline errors | ✅ |  |
| admin | desktop | Create project | valid project is created and a success toast shows | ✅ |  |
| admin | desktop | Dialogs | Log progress dialog traps focus and closes on Escape | ✅ |  |
| admin | desktop | Progress scenario | negative total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| admin | desktop | Progress scenario | non-numeric total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| admin | desktop | Progress scenario | log 600 -> success toast | ✅ |  |
| admin | desktop | Progress scenario | log 850 -> success toast, page shows 85% | ✅ |  |
| admin | desktop | Progress scenario | history shows 600 → 850 with author | ✅ | Asha Rao · 5 Nov 2026, 12:01 pm |
| admin | desktop | Progress scenario | decrease without a reason is rejected | ✅ | The total is going down. Tick this box and explain why. |
| admin | desktop | Progress scenario | project list shows 85% without reload | ✅ |  |
| admin | desktop | Dashboard | dashboard figures changed after logging progress (no reload) | ✅ |  |
| admin | desktop | Edit project | edit own project -> success toast | ✅ |  |
| admin | desktop | Undo progress | undo asks for confirmation; Escape cancels | ✅ |  |
| admin | desktop | Undo progress | confirmed undo -> success toast, total back to 600 | ✅ |  |
| admin | desktop | Delete project | delete asks for confirmation; Escape cancels | ✅ |  |
| admin | desktop | Delete project | confirmed delete -> success toast and back to the list | ✅ |  |
| admin | desktop | User management | own row controls are disabled | ✅ |  |
| admin | desktop | User management | role change -> success toast | ✅ |  |
| admin | desktop | User management | deactivate asks for confirmation, then toast | ✅ |  |
| admin | desktop | User management | reactivate -> success toast | ✅ |  |
| admin | desktop | Toasts | a failed mutation shows an error toast with the server message | ✅ |  |
| admin | desktop | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| admin | desktop | Toasts | failed export shows an error toast | ✅ |  |
| admin | desktop | Activity | activity page lists entries | ✅ | 50 entries |
| admin | desktop | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| admin | desktop | Users page access | admin sees Users link | ✅ |  |
| admin | desktop | Layout / navigation | visible focus ring on keyboard focus | ✅ | A auto 1px |
| admin | desktop | Logout | log out -> info toast and back on the login page | ✅ |  |
| admin | desktop | Console | no JavaScript errors in the console | ✅ |  |
| manager | desktop | Login | valid login lands on the dashboard | ✅ |  |
| manager | desktop | Create project | empty form is rejected with inline errors | ✅ |  |
| manager | desktop | Create project | valid project is created and a success toast shows | ✅ |  |
| manager | desktop | Dialogs | Log progress dialog traps focus and closes on Escape | ✅ |  |
| manager | desktop | Progress scenario | negative total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager | desktop | Progress scenario | non-numeric total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager | desktop | Progress scenario | log 600 -> success toast | ✅ |  |
| manager | desktop | Progress scenario | log 850 -> success toast, page shows 85% | ✅ |  |
| manager | desktop | Progress scenario | history shows 600 → 850 with author | ✅ | Ravi Kumar · 5 Nov 2026, 12:01 pm |
| manager | desktop | Progress scenario | decrease without a reason is rejected | ✅ | The total is going down. Tick this box and explain why. |
| manager | desktop | Progress scenario | project list shows 85% without reload | ✅ |  |
| manager | desktop | Dashboard | dashboard figures changed after logging progress (no reload) | ✅ |  |
| manager | desktop | Edit project | edit own project -> success toast | ✅ |  |
| manager | desktop | Undo progress | undo button hidden for non-admin | ✅ |  |
| manager | desktop | Permissions | another owner's project hides Edit/Delete/Log progress | ✅ |  |
| manager | desktop | Permissions | editing another owner's project shows Not authorized | ✅ |  |
| manager | desktop | Permissions | API returns 403 with a clear message on another owner's project | ✅ | 403: You can only modify projects you own. |
| manager | desktop | Delete project | delete asks for confirmation; Escape cancels | ✅ |  |
| manager | desktop | Delete project | confirmed delete -> success toast and back to the list | ✅ |  |
| manager | desktop | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| manager | desktop | Toasts | failed export shows an error toast | ✅ |  |
| manager | desktop | Activity | activity page lists entries | ✅ | 50 entries |
| manager | desktop | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| manager | desktop | Users page access | Users link hidden; /users shows Not authorized | ✅ |  |
| manager | desktop | Layout / navigation | visible focus ring on keyboard focus | ✅ | A auto 1px |
| manager | desktop | Logout | log out -> info toast and back on the login page | ✅ |  |
| manager | desktop | Console | no JavaScript errors in the console | ✅ |  |
| manager2 | desktop | Login | valid login lands on the dashboard | ✅ |  |
| manager2 | desktop | Create project | empty form is rejected with inline errors | ✅ |  |
| manager2 | desktop | Create project | valid project is created and a success toast shows | ✅ |  |
| manager2 | desktop | Dialogs | Log progress dialog traps focus and closes on Escape | ✅ |  |
| manager2 | desktop | Progress scenario | negative total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager2 | desktop | Progress scenario | non-numeric total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager2 | desktop | Progress scenario | log 600 -> success toast | ✅ |  |
| manager2 | desktop | Progress scenario | log 850 -> success toast, page shows 85% | ✅ |  |
| manager2 | desktop | Progress scenario | history shows 600 → 850 with author | ✅ | Meera Iyer · 5 Nov 2026, 12:01 pm |
| manager2 | desktop | Progress scenario | decrease without a reason is rejected | ✅ | The total is going down. Tick this box and explain why. |
| manager2 | desktop | Progress scenario | project list shows 85% without reload | ✅ |  |
| manager2 | desktop | Dashboard | dashboard figures changed after logging progress (no reload) | ✅ |  |
| manager2 | desktop | Edit project | edit own project -> success toast | ✅ |  |
| manager2 | desktop | Undo progress | undo button hidden for non-admin | ✅ |  |
| manager2 | desktop | Permissions | another owner's project hides Edit/Delete/Log progress | ✅ |  |
| manager2 | desktop | Permissions | editing another owner's project shows Not authorized | ✅ |  |
| manager2 | desktop | Permissions | API returns 403 with a clear message on another owner's project | ✅ | 403: You can only modify projects you own. |
| manager2 | desktop | Delete project | delete asks for confirmation; Escape cancels | ✅ |  |
| manager2 | desktop | Delete project | confirmed delete -> success toast and back to the list | ✅ |  |
| manager2 | desktop | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| manager2 | desktop | Toasts | failed export shows an error toast | ✅ |  |
| manager2 | desktop | Activity | activity page lists entries | ✅ | 50 entries |
| manager2 | desktop | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| manager2 | desktop | Users page access | Users link hidden; /users shows Not authorized | ✅ |  |
| manager2 | desktop | Layout / navigation | visible focus ring on keyboard focus | ✅ | A auto 1px |
| manager2 | desktop | Logout | log out -> info toast and back on the login page | ✅ |  |
| manager2 | desktop | Console | no JavaScript errors in the console | ✅ |  |
| viewer | desktop | Login | valid login lands on the dashboard | ✅ |  |
| viewer | desktop | Create project | New project button hidden for viewer | ✅ |  |
| viewer | desktop | Create project | /projects/new shows Not authorized | ✅ |  |
| viewer | desktop | Create project | API refuses create with 403 | ✅ | 403: "Your role (viewer) cannot perform this action." |
| viewer | desktop | Permissions | project page hides Edit/Delete/Log progress | ✅ |  |
| viewer | desktop | Permissions | edit URL shows Not authorized | ✅ |  |
| viewer | desktop | Permissions | API returns 403 on edit and on logging progress | ✅ | 403: You can only modify projects you own. |
| viewer | desktop | Dashboard | dashboard loads with figures | ✅ |  |
| viewer | desktop | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| viewer | desktop | Toasts | failed export shows an error toast | ✅ |  |
| viewer | desktop | Activity | activity page lists entries | ✅ | 50 entries |
| viewer | desktop | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| viewer | desktop | Users page access | Users link hidden; /users shows Not authorized | ✅ |  |
| viewer | desktop | Layout / navigation | visible focus ring on keyboard focus | ✅ | A auto 1px |
| viewer | desktop | Logout | log out -> info toast and back on the login page | ✅ |  |
| viewer | desktop | Console | no JavaScript errors in the console | ✅ |  |
| anonymous | mobile | Login | wrong password shows a clear error | ✅ | Incorrect email or password. |
| anonymous | mobile | Register | mismatched passwords rejected inline | ✅ |  |
| anonymous | mobile | Register | valid registration -> welcome toast, logged in as viewer | ✅ |  |
| anonymous | mobile | Not found / status | /status page reports API and database connected | ✅ |  |
| admin | mobile | Login | valid login lands on the dashboard | ✅ |  |
| admin | mobile | Create project | empty form is rejected with inline errors | ✅ |  |
| admin | mobile | Create project | valid project is created and a success toast shows | ✅ |  |
| admin | mobile | Dialogs | Log progress dialog traps focus and closes on Escape | ✅ |  |
| admin | mobile | Progress scenario | negative total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| admin | mobile | Progress scenario | non-numeric total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| admin | mobile | Progress scenario | log 600 -> success toast | ✅ |  |
| admin | mobile | Progress scenario | log 850 -> success toast, page shows 85% | ✅ |  |
| admin | mobile | Progress scenario | history shows 600 → 850 with author | ✅ | Asha Rao · 5 Nov 2026, 12:02 pm |
| admin | mobile | Progress scenario | decrease without a reason is rejected | ✅ | The total is going down. Tick this box and explain why. |
| admin | mobile | Progress scenario | project list shows 85% without reload | ✅ |  |
| admin | mobile | Dashboard | dashboard figures changed after logging progress (no reload) | ✅ |  |
| admin | mobile | Edit project | edit own project -> success toast | ✅ |  |
| admin | mobile | Undo progress | undo asks for confirmation; Escape cancels | ✅ |  |
| admin | mobile | Undo progress | confirmed undo -> success toast, total back to 600 | ✅ |  |
| admin | mobile | Delete project | delete asks for confirmation; Escape cancels | ✅ |  |
| admin | mobile | Delete project | confirmed delete -> success toast and back to the list | ✅ |  |
| admin | mobile | User management | own row controls are disabled | ✅ |  |
| admin | mobile | User management | role change -> success toast | ✅ |  |
| admin | mobile | User management | deactivate asks for confirmation, then toast | ✅ |  |
| admin | mobile | User management | reactivate -> success toast | ✅ |  |
| admin | mobile | Toasts | a failed mutation shows an error toast with the server message | ✅ |  |
| admin | mobile | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| admin | mobile | Toasts | failed export shows an error toast | ✅ |  |
| admin | mobile | Activity | activity page lists entries | ✅ | 50 entries |
| admin | mobile | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| admin | mobile | Users page access | admin sees Users link | ✅ |  |
| admin | mobile | Layout / navigation | mobile menu traps focus, Escape closes it and focus returns to the menu button | ✅ |  |
| admin | mobile | Layout / navigation | visible focus ring on keyboard focus | ✅ | BUTTON solid 2px |
| admin | mobile | Logout | log out -> info toast and back on the login page | ✅ |  |
| admin | mobile | Console | no JavaScript errors in the console | ✅ |  |
| manager | mobile | Login | valid login lands on the dashboard | ✅ |  |
| manager | mobile | Create project | empty form is rejected with inline errors | ✅ |  |
| manager | mobile | Create project | valid project is created and a success toast shows | ✅ |  |
| manager | mobile | Dialogs | Log progress dialog traps focus and closes on Escape | ✅ |  |
| manager | mobile | Progress scenario | negative total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager | mobile | Progress scenario | non-numeric total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager | mobile | Progress scenario | log 600 -> success toast | ✅ |  |
| manager | mobile | Progress scenario | log 850 -> success toast, page shows 85% | ✅ |  |
| manager | mobile | Progress scenario | history shows 600 → 850 with author | ✅ | Ravi Kumar · 5 Nov 2026, 12:02 pm |
| manager | mobile | Progress scenario | decrease without a reason is rejected | ✅ | The total is going down. Tick this box and explain why. |
| manager | mobile | Progress scenario | project list shows 85% without reload | ✅ |  |
| manager | mobile | Dashboard | dashboard figures changed after logging progress (no reload) | ✅ |  |
| manager | mobile | Edit project | edit own project -> success toast | ✅ |  |
| manager | mobile | Undo progress | undo button hidden for non-admin | ✅ |  |
| manager | mobile | Permissions | another owner's project hides Edit/Delete/Log progress | ✅ |  |
| manager | mobile | Permissions | editing another owner's project shows Not authorized | ✅ |  |
| manager | mobile | Permissions | API returns 403 with a clear message on another owner's project | ✅ | 403: You can only modify projects you own. |
| manager | mobile | Delete project | delete asks for confirmation; Escape cancels | ✅ |  |
| manager | mobile | Delete project | confirmed delete -> success toast and back to the list | ✅ |  |
| manager | mobile | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| manager | mobile | Toasts | failed export shows an error toast | ✅ |  |
| manager | mobile | Activity | activity page lists entries | ✅ | 50 entries |
| manager | mobile | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| manager | mobile | Users page access | Users link hidden; /users shows Not authorized | ✅ |  |
| manager | mobile | Layout / navigation | mobile menu traps focus, Escape closes it and focus returns to the menu button | ✅ |  |
| manager | mobile | Layout / navigation | visible focus ring on keyboard focus | ✅ | BUTTON solid 2px |
| manager | mobile | Logout | log out -> info toast and back on the login page | ✅ |  |
| manager | mobile | Console | no JavaScript errors in the console | ✅ |  |
| manager2 | mobile | Login | valid login lands on the dashboard | ✅ |  |
| manager2 | mobile | Create project | empty form is rejected with inline errors | ✅ |  |
| manager2 | mobile | Create project | valid project is created and a success toast shows | ✅ |  |
| manager2 | mobile | Dialogs | Log progress dialog traps focus and closes on Escape | ✅ |  |
| manager2 | mobile | Progress scenario | negative total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager2 | mobile | Progress scenario | non-numeric total rejected with a message | ✅ | Enter a whole number, like 850 (no commas, decimals or minus sign). |
| manager2 | mobile | Progress scenario | log 600 -> success toast | ✅ |  |
| manager2 | mobile | Progress scenario | log 850 -> success toast, page shows 85% | ✅ |  |
| manager2 | mobile | Progress scenario | history shows 600 → 850 with author | ✅ | Meera Iyer · 5 Nov 2026, 12:02 pm |
| manager2 | mobile | Progress scenario | decrease without a reason is rejected | ✅ | The total is going down. Tick this box and explain why. |
| manager2 | mobile | Progress scenario | project list shows 85% without reload | ✅ |  |
| manager2 | mobile | Dashboard | dashboard figures changed after logging progress (no reload) | ✅ |  |
| manager2 | mobile | Edit project | edit own project -> success toast | ✅ |  |
| manager2 | mobile | Undo progress | undo button hidden for non-admin | ✅ |  |
| manager2 | mobile | Permissions | another owner's project hides Edit/Delete/Log progress | ✅ |  |
| manager2 | mobile | Permissions | editing another owner's project shows Not authorized | ✅ |  |
| manager2 | mobile | Permissions | API returns 403 with a clear message on another owner's project | ✅ | 403: You can only modify projects you own. |
| manager2 | mobile | Delete project | delete asks for confirmation; Escape cancels | ✅ |  |
| manager2 | mobile | Delete project | confirmed delete -> success toast and back to the list | ✅ |  |
| manager2 | mobile | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| manager2 | mobile | Toasts | failed export shows an error toast | ✅ |  |
| manager2 | mobile | Activity | activity page lists entries | ✅ | 50 entries |
| manager2 | mobile | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| manager2 | mobile | Users page access | Users link hidden; /users shows Not authorized | ✅ |  |
| manager2 | mobile | Layout / navigation | mobile menu traps focus, Escape closes it and focus returns to the menu button | ✅ |  |
| manager2 | mobile | Layout / navigation | visible focus ring on keyboard focus | ✅ | BUTTON solid 2px |
| manager2 | mobile | Logout | log out -> info toast and back on the login page | ✅ |  |
| manager2 | mobile | Console | no JavaScript errors in the console | ✅ |  |
| viewer | mobile | Login | valid login lands on the dashboard | ✅ |  |
| viewer | mobile | Create project | New project button hidden for viewer | ✅ |  |
| viewer | mobile | Create project | /projects/new shows Not authorized | ✅ |  |
| viewer | mobile | Create project | API refuses create with 403 | ✅ | 403: "Your role (viewer) cannot perform this action." |
| viewer | mobile | Permissions | project page hides Edit/Delete/Log progress | ✅ |  |
| viewer | mobile | Permissions | edit URL shows Not authorized | ✅ |  |
| viewer | mobile | Permissions | API returns 403 on edit and on logging progress | ✅ | 403: You can only modify projects you own. |
| viewer | mobile | Dashboard | dashboard loads with figures | ✅ |  |
| viewer | mobile | Export CSV | export -> file downloaded and success toast | ✅ | vanatrack-projects-2026-11-05.csv |
| viewer | mobile | Toasts | failed export shows an error toast | ✅ |  |
| viewer | mobile | Activity | activity page lists entries | ✅ | 50 entries |
| viewer | mobile | Not found / status | unknown URL shows the 404 page inside the app | ✅ |  |
| viewer | mobile | Users page access | Users link hidden; /users shows Not authorized | ✅ |  |
| viewer | mobile | Layout / navigation | mobile menu traps focus, Escape closes it and focus returns to the menu button | ✅ |  |
| viewer | mobile | Layout / navigation | visible focus ring on keyboard focus | ✅ | BUTTON solid 2px |
| viewer | mobile | Logout | log out -> info toast and back on the login page | ✅ |  |
| viewer | mobile | Console | no JavaScript errors in the console | ✅ |  |

<!-- COUNTS flows=212 failed=0 states=254 failed=0 audit=132 -->

</details>
