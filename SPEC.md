# Polling App — Full-Stack Build Specification

## 1. What you're building
A live audience-polling app for a physical room (100–150 people). Admin controls a single active poll with exactly 2 editable options. Attendees open one shared link, pick their name, vote once, and see nothing else. Admin sees a live tally, who has/hasn't voted, and can close a round into a ranked result or start a fresh round.

## 2. Roles
- **Admin**: Secret login. Manage participant roster, edit poll question + 2 options, watch live results, close/reset rounds.
- **Voter**: No login. Opens the public link, votes once, done.

## 3. Name-based identity
Named roster + shared link. Admin bulk-adds the 100–150 names beforehand. Everyone uses the same link. On load, voter types/searches their name (fast typeahead over ~150 names), picks an option, submits. Server marks that participant's row as voted — a second attempt with the same name is rejected.

## 4. Close vs Reset
- **"Close Round"** — locks voting, freezes the tally, shows ranked results (winner/runner-up by vote count). Non-destructive, reversible by reopening.
- **"Reset Round"** — separate button, requires a confirm dialog, wipes votes + voted-status (roster and option text survive) to start a new round. Only enabled after a round is closed.

## 5. Functional Requirements
### Admin
- Login via secret credentials
- Add participants: single add + bulk paste
- Remove/edit a participant
- Edit poll question and both option labels (only while draft)
- Open voting (draft -> active)
- Live dashboard
- Close Round -> ranked result view
- Reset Round -> confirm dialog

### Voter
- Opens the single shared link
- Sees: poll question, 2 options, name search box
- Selects name, selects option, submits
- Gets a clear "your vote is recorded" state

## 7. Tech Stack
- Backend: FastAPI (Python)
- DB: PostgreSQL
- Frontend: Next.js (App Router) + Tailwind
- Real-time: polling (`GET /admin/results` every 2s)

## 8. Data Model
`admins`, `polls`, `participants` tables.

## 9. API Design
Admin: `/api/admin/login`, `/api/admin/participants`, `/api/admin/poll`, `/api/admin/poll/open`, `/api/admin/poll/close`, `/api/admin/poll/reset`, `/api/admin/results`
Public: `/api/poll`, `/api/participants/search`, `/api/vote`
