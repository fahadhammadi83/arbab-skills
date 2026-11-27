# Sending: mailboxes, safety checks, scheduling

## Which mode
| What the user has connected | Mode | How a send works |
|---|---|---|
| Gmail (`send_message`, `create_draft`, `search_threads`) | **Send** or **Draft** | `send_message` to one address, plain text. Draft mode: `create_draft`, and the user presses send |
| Outlook / Microsoft 365 (`outlook_send_mail`, `outlook_create_draft`, `outlook_email_search`) | **Send** or **Draft** | `outlook_send_mail` with `bodyType: "text"`, one recipient. Draft mode: `outlook_create_draft` |
| Nothing | **Draft file** | The user copies each email from `batch.md` and sends it, then tells you which went so you can run `mark <id> sent` |

Ask once which mode the user wants. **Draft mode is the safest start:** the emails wait in their mailbox and they press send. Run `mark <id> sent` only after they confirm.

Always send from the user's own business mailbox, never a personal one, unless they say so.

## Before every send (when a mailbox is connected)
1. **Warnings:** search today's inbox for messages from the mail provider about "suspicious sending", "unusual activity", "sending limit" or "restricted". If one arrived, run `halt "<provider> warning <time>"`, tell the user, and stop.
2. **Bounces:** search today and yesterday for "Undeliverable", "Delivery has failed", "Delivery Status Notification" and "Mail delivery failed". For each one about an address in `outreach/log.csv`, run `mark <id> bounced --date <send day>`.
3. **Replies:** a human reply from a logged company's domain means `mark <id> replied`. Don't answer it. Tell the user who replied and the gist.

## Why one at a time and spaced
Mail providers flag accounts that send many similar emails in a burst. One email every 15+ minutes, a daily cap, different text in each email and no CC keep the account looking like a person, because it is one.
- **New mailbox:** start at 5 a day for the first week, then 10, then up to 20.
- **Count everything:** if the user also sends their own external emails, keep the outreach cap lower so the day's total stays reasonable.

## Sending through the day (scheduled)
After the user approves a batch, the sending can run on a schedule. In the Claude desktop app (Code tab), ask for a scheduled task that runs every 20 minutes on sending days inside the window with this prompt:

> Use the prospect-emails skill, Step 6 only, for today. Run the safety checks, then `next`. Send at most ONE email, exactly as given, then `mark` it. If you get WAIT or DONE, send nothing. Never approve anything.

The tool refuses anything not approved, outside the window, over the cap, too soon after the last send, or after a HALT or STOP. So a scheduled run can't send more than the user agreed.

**Two computers?** Run the schedule on one only, or the same email could go twice.
