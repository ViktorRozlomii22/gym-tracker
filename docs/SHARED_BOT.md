# Invitation-only shared bot

The existing paired owner remains the administrator after upgrade. Invitees share
one running bot and SQLite database on the host PC. Records are scoped to Telegram
user IDs. The host operator can read the complete database and backups; this is
not end-to-end encryption between the user and the database.

## Invite someone

1. As administrator, send `/invite` or open **More → Members**.
2. Share the generated link with the intended person yourself.
3. The person opens it and presses Start. Their Telegram account becomes a member.

Each invitation can be redeemed once, expires after seven days, and is stored only
as a SHA-256 digest. It is a bearer link: the first eligible account that uses it
receives access. For now it is not bound to a predetermined Telegram ID. Keep it
private. `/revokeinvite NUMBER` invalidates an unused invitation. A used or expired
link cannot admit another account. Concurrent redemption admits only one account.

`/invites` lists up to 100 latest active, unused invitations with their numbers and UTC expiry times. It omits used, revoked and expired links and never reveals link secrets. Use its numbers with `/revokeinvite NUMBER`.

`/members` lists invited Telegram IDs and access status. `/blockuser ID` suspends
access without deleting records; `/unblockuser ID` restores it. A blocked account
cannot rejoin using another invitation. These commands cannot suspend the owner.
Group chats are rejected. `/account` shows only the caller's ID and role.

## Permissions

| Capability | Administrator | Invited member |
| --- | --- | --- |
| Own diary, actual sets and notes | Yes | Yes |
| Own measurements, history, graphs and exports | Yes | Yes |
| Own inactivity reminders and Sunday reports | Yes | Yes |
| AI generation, questions and parsing | Yes | No |
| Invitation and membership management | Yes | No |
| Whole-database backup controls | Yes | No |

AI restrictions apply to direct commands, Telegram menu buttons and background
inference. Model parsing also checks permission before calling Ollama. There is no
payment integration or purchasable AI entitlement yet: only the owner may use AI.
Ordinary diary entry does not need the model. Members have a smaller home menu;
the administrator has a private Telegram command scope with management commands.

Each member enables `/remind DAYS` and `/weeklyremind on` separately. A failed
delivery to one recipient does not prevent delivery to other active members.
Existing owner reminder preferences continue to work. Reminders require the host
PC and bot to remain running; times use the host PC's local clock.

Clearing one's diary removes personal settings and invalidates pending AI results.
It retains membership and suspension status. Host backups can retain earlier
records until rotated out; deleting a diary is not an erasure of existing backups.
Restoring a whole database also restores the membership and invitation state at
backup time. Recheck memberships and revoke restored outstanding invitations
before admitting users after a restore.

## Acceptance and deployment

Automated tests cover expiry, single use, concurrent redemption, revocation,
suspension, role checks, private exports and note edits, reminders, and deletion.
They use synthetic accounts and temporary databases. Before calling the shared
bot fully accepted, exercise the complete flow with two real Telegram accounts:
invite, start, independently record/export data, deny member AI and backups,
suspend, reject reuse, restore access, and check persistence after a restart.

Upgrade by stopping the old bot, keeping its private `data/` folder, and starting
the updated executable once. Schema additions are backward compatible. Do not run
two instances with the same token. Publishing a GitHub release is a separate
action from pushing source commits.
