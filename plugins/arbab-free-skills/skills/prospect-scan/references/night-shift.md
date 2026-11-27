# Night shift: run the scan every night

Each run takes the next 50 businesses from the list and remembers what's done in `scanned.csv`. On a schedule, you wake up to 5 businesses to contact every morning.

## Option 1 · Claude scheduled task (easiest)
In the Claude desktop app (Code tab), ask: "Create a scheduled task that runs the prospect-scan skill every Sunday to Thursday at 22:00 on my list `<path>`, and saves the top 5." Your computer must be on at that time.

The task prompt should say:
1. Use the prospect-scan skill on `<list path>` with output folder `<folder>`.
2. Steps 2 to 4 only. Never send anything.
3. If it prints STOPPED or QUEUE EMPTY, say so and stop.

## Option 2 · Cloud (runs with the computer off)
Put the script and your list in a private GitHub repository. Then create a Claude Code cloud scheduled task on that repo with the same prompt. The list must live in the repo, because the cloud can't see your computer's files. Keep the repo **private** if the list has phone numbers.

## Kill switch
Create an empty file named `STOP` in the output folder. The script refuses to scan until you delete it. Or switch the scheduled task off.

## Good habits
- Keep the batch at 50 or below. Reading hundreds of sites at once looks like an attack to some servers.
- Feed the queue: when it says QUEUE EMPTY, add a new list with another `--list`.
- Contact each business once, by hand. Follow up at most twice, and stop the moment they say no.
