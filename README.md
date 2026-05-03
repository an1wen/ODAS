# ODAS
Onlyfans Detected - Account Suspended

The proejct is meant to work in two steps:
- one script checks accounts for unwanted content
- one script reads database and mass-block undesirable accounts

## Scan

Run with:
```
python3 odas_finder.py
```
Files in the repo:
1. Whitelist: loads list of people you follow, and people following you, and makes a whitelist out of it. Whitelist people are always skipped (for scanning or blocking).
2. Processed: loads list of accounts already processed (and all info extracted from there).
3. Checklist: list made of accounts that are needed to be checked.

Default behavior:
1. Loads whitelist, processed list, and checklist. Adds "suspect zero" to checklist if provided.
2. Starts scanning accounts in the checklist. Skips if account in whitelist/processed list.
3. Looks for keywords, whether it finds keywords or not it writes the result to file.

## Block

Run with:
```
python3 odas_blocker.py
```
Default behavior:
1. Loads whitelist and processed list.
2. Go through processed list.
3. Skips if account in whitelist/processed list.
4. If triggers contain keywords, then block.

## Disclaimer

This is a volunteer project, and I am a lousy programmer. I do not guarantee your safety, the safety of your computer, or the safety of your instagram account:
1. The use of bots/API is forbidden by Instagram. If they catch you, that's on you.
2. Data scraping is forbidden by Instagram. If they catch you, that's on you.
3. This repo uses libraries such as instagrapi and selenium. If they get compromised/become unsafe for your computer, that's on you.

Have fun!
